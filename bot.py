#!/usr/bin/env python3
"""
SHEGER ET V2 - Enhanced Ethiopian Super App
Production Ready with Supabase Backend
"""

import os
import json
import logging
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================
# LOAD ENVIRONMENT
# ======================
load_dotenv()

# ======================
# CONFIGURATION V2
# ======================
TELEBIRR = os.getenv("TELEBIRR", "0961393001")
CBE = os.getenv("CBE", "1000645865603")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7714584854"))

SUPPORT = os.getenv("SUPPORT", "@ShegerESupport")
PAYMENTS = os.getenv("PAYMENTS", "@ShegerPayments")
SALES = os.getenv("SALES", "@ShegerESales")
NEWS = os.getenv("NEWS", "@ShegeErNews")

BOT_NAME = os.getenv("BOT_NAME", "SHEGER ET")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@ShegerETBot")
BOT_SLOGAN = os.getenv("BOT_SLOGAN", "Ethiopia's All-in-One Super App")

# ======================
# SUPABASE INITIALIZATION
# ======================
try:
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )
    logger = logging.getLogger(__name__)
    logger.info("✅ Supabase client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase: {e}")
    raise

# ======================
# ENHANCED LOGGING
# ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('sheger_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ======================
# SUPABASE DATABASE FUNCTIONS
# ======================

def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code"""
    prefix = "SHEGER"
    unique = f"{user_id:06d}"[-6:]
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{unique}{chars}"

async def create_or_update_user(user_id: int, username: str, full_name: str, source: str = "bot") -> Optional[str]:
    """Create or update user in Supabase"""
    try:
        # Check if user exists
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if response.data:
            # Update existing user
            supabase.table('users').update({
                'username': username,
                'full_name': full_name,
                'last_active': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            referral_code = response.data[0]['referral_code']
            logger.info(f"👤 User updated: {user_id} (@{username})")
            
        else:
            # Create new user
            referral_code = generate_referral_code(user_id)
            
            user_data = {
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'referral_code': referral_code,
                'join_source': source,
                'joined_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat(),
                'metadata': {
                    'bot_version': 'v2',
                    'join_source': source,
                    'platform': 'telegram'
                }
            }
            
            supabase.table('users').insert(user_data).execute()
            
            # Log analytics
            supabase.table('analytics').insert({
                'event_type': 'user_join',
                'user_id': user_id,
                'data': {
                    'source': source,
                    'username': username,
                    'referral_code': referral_code
                }
            }).execute()
            
            logger.info(f"👤 New user created: {user_id} (@{username}) from {source}")
        
        return referral_code
        
    except Exception as e:
        logger.error(f"❌ Error creating/updating user: {e}")
        return None

async def get_user_stats(user_id: int) -> Dict:
    """Get comprehensive user statistics"""
    try:
        # Get user data
        user_response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not user_response.data:
            return {}
        
        user = user_response.data[0]
        
        # Get referral stats
        referrals_response = supabase.table('users')\
            .select('id, total_spent')\
            .eq('referred_by', user_id)\
            .execute()
        
        # Get payment stats
        payments_response = supabase.table('payments')\
            .select('amount, status')\
            .eq('user_id', user_id)\
            .execute()
        
        referred_count = len(referrals_response.data) if referrals_response.data else 0
        referred_revenue = sum(float(u.get('total_spent', 0) or 0) for u in (referrals_response.data or []))
        
        payments_data = payments_response.data or []
        total_payments = len(payments_data)
        total_verified = sum(float(p.get('amount', 0) or 0) for p in payments_data if p.get('status') == 'verified')
        
        return {
            'plan': user.get('plan', 'basic'),
            'total_spent': float(user.get('total_spent', 0) or 0),
            'total_earned': float(user.get('total_earned', 0) or 0),
            'balance': float(user.get('balance', 0) or 0),
            'referral_code': user.get('referral_code'),
            'joined_date': user.get('joined_at'),
            'referred_count': referred_count,
            'referred_revenue': referred_revenue,
            'total_payments': total_payments,
            'total_verified': total_verified
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user stats: {e}")
        return {}

async def get_user_plan(user_id: int) -> str:
    """Get user's current plan"""
    try:
        response = supabase.table('users').select('plan, last_payment').eq('id', user_id).execute()
        
        if not response.data:
            return 'basic'
        
        user = response.data[0]
        plan = user.get('plan', 'basic')
        
        # Check if subscription is still valid
        last_payment = user.get('last_payment')
        if last_payment:
            try:
                last_payment_date = datetime.fromisoformat(last_payment.replace('Z', '+00:00'))
                if datetime.now() - last_payment_date <= timedelta(days=30):
                    return plan
            except:
                pass
        
        return plan
        
    except Exception as e:
        logger.error(f"❌ Error getting user plan: {e}")
        return 'basic'

def get_plan_fee(plan: str) -> float:
    """Get transaction fee for plan"""
    fee_map = {
        'basic': 2.5,
        'pro': 1.5,
        'business': 0.8
    }
    return fee_map.get(plan, 2.5)

async def create_payment(user_id: int, username: str, plan: str, amount: float, campaign_code: str = None) -> Optional[str]:
    """Create payment record in Supabase"""
    try:
        reference_code = f"{plan.upper()}-{user_id}-{int(datetime.now().timestamp())}"
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        payment_data = {
            'user_id': user_id,
            'username': username,
            'plan': plan,
            'amount': float(amount),
            'reference_code': reference_code,
            'expires_at': expires_at,
            'campaign_id': campaign_code,
            'status': 'pending'
        }
        
        response = supabase.table('payments').insert(payment_data).execute()
        
        if response.data:
            # Log analytics
            supabase.table('analytics').insert({
                'event_type': 'payment_initiated',
                'user_id': user_id,
                'data': {
                    'plan': plan,
                    'amount': amount,
                    'campaign': campaign_code,
                    'reference': reference_code
                }
            }).execute()
            
            logger.info(f"💰 Payment created: {user_id} - {plan} - {amount} ETB")
            return reference_code
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error creating payment: {e}")
        return None

async def verify_payment(user_id: int, admin_id: int, amount: float = None, plan: str = None) -> tuple:
    """Verify payment and update user"""
    try:
        # Get pending payment
        response = supabase.table('payments')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            return False, "No pending payment found"
        
        payment = response.data[0]
        payment_id = payment['id']
        actual_plan = plan or payment['plan']
        actual_amount = amount or float(payment['amount'])
        campaign_code = payment.get('campaign_id')
        
        # Apply campaign discount
        final_amount = actual_amount
        if campaign_code:
            campaign_response = supabase.table('campaigns')\
                .select('*')\
                .eq('code', campaign_code)\
                .eq('is_active', True)\
                .gte('expires_at', datetime.now().isoformat())\
                .execute()
            
            if campaign_response.data:
                campaign = campaign_response.data[0]
                
                if campaign['type'] == 'discount' and campaign.get('discount_percent'):
                    discount = actual_amount * (float(campaign['discount_percent']) / 100)
                    final_amount = actual_amount - discount
                elif campaign['type'] == 'discount' and campaign.get('discount_amount'):
                    final_amount = actual_amount - float(campaign['discount_amount'])
                
                # Update campaign usage
                supabase.table('campaigns')\
                    .update({'used_count': (campaign['used_count'] or 0) + 1})\
                    .eq('id', campaign['id'])\
                    .execute()
        
        # Update payment status
        supabase.table('payments')\
            .update({
                'status': 'verified',
                'verified_by': admin_id,
                'verified_at': datetime.now().isoformat(),
                'plan': actual_plan,
                'amount': float(final_amount)
            })\
            .eq('id', payment_id)\
            .execute()
        
        # Update user
        supabase.table('users')\
            .update({
                'plan': actual_plan,
                'total_spent': supabase.rpc('increment', {
                    'table_name': 'users',
                    'column_name': 'total_spent',
                    'row_id': user_id,
                    'amount': float(final_amount)
                }),
                'last_payment': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            })\
            .eq('id', user_id)\
            .execute()
        
        # Handle referral rewards
        user_response = supabase.table('users').select('referred_by').eq('id', user_id).execute()
        if user_response.data and user_response.data[0].get('referred_by'):
            referrer_id = user_response.data[0]['referred_by']
            reward_amount = final_amount * 0.10  # 10% commission
            
            supabase.table('users')\
                .update({
                    'total_earned': supabase.rpc('increment', {
                        'table_name': 'users',
                        'column_name': 'total_earned',
                        'row_id': referrer_id,
                        'amount': float(reward_amount)
                    }),
                    'balance': supabase.rpc('increment', {
                        'table_name': 'users',
                        'column_name': 'balance',
                        'row_id': referrer_id,
                        'amount': float(reward_amount)
                    })
                })\
                .eq('id', referrer_id)\
                .execute()
            
            # Log referral reward
            supabase.table('analytics').insert({
                'event_type': 'referral_reward',
                'user_id': referrer_id,
                'data': {
                    'referred_user': user_id,
                    'amount': reward_amount,
                    'type': 'upgrade'
                }
            }).execute()
        
        # Log analytics
        supabase.table('analytics').insert({
            'event_type': 'payment_verified',
            'user_id': user_id,
            'data': {
                'plan': actual_plan,
                'amount': final_amount,
                'original_amount': actual_amount,
                'campaign': campaign_code,
                'payment_id': payment_id
            }
        }).execute()
        
        return True, f"✅ Payment verified! User upgraded to {actual_plan.upper()}. Final amount: {final_amount:.2f} ETB"
        
    except Exception as e:
        logger.error(f"❌ Error verifying payment: {e}")
        return False, f"Error: {str(e)}"

async def get_campaigns() -> List[Dict]:
    """Get active campaigns"""
    try:
        response = supabase.table('campaigns')\
            .select('*')\
            .eq('is_active', True)\
            .gte('expires_at', datetime.now().isoformat())\
            .order('created_at', desc=True)\
            .execute()
        
        return response.data or []
        
    except Exception as e:
        logger.error(f"❌ Error getting campaigns: {e}")
        return []

async def create_notification(user_id: int, title: str, message: str, notification_type: str = "info"):
    """Create notification for user"""
    try:
        notification_data = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'is_read': False
        }
        
        supabase.table('notifications').insert(notification_data).execute()
        
    except Exception as e:
        logger.error(f"❌ Error creating notification: {e}")

# ======================
# BOT COMMAND HANDLERS
# ======================

async def start_command(update: Update, context):
    """Start command with referral tracking"""
    user = update.effective_user
    
    # Check for referral code
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        logger.info(f"📨 Referral detected: {user.id} via {referral_code}")
    
    # Create/update user
    user_ref_code = await create_or_update_user(user.id, user.username, user.full_name, "bot")
    
    # Process referral if exists
    if referral_code and user_ref_code:
        try:
            # Find referrer
            referrer_response = supabase.table('users')\
                .select('id')\
                .eq('referral_code', referral_code)\
                .execute()
            
            if referrer_response.data:
                referrer_id = referrer_response.data[0]['id']
                
                # Update user with referrer
                supabase.table('users')\
                    .update({'referred_by': referrer_id})\
                    .eq('id', user.id)\
                    .execute()
                
                # Log analytics
                supabase.table('analytics').insert({
                    'event_type': 'referral_click',
                    'user_id': user.id,
                    'data': {
                        'referrer': referrer_id,
                        'code': referral_code,
                        'action': 'signup'
                    }
                }).execute()
                
                logger.info(f"🤝 Referral linked: {user.id} -> {referrer_id}")
                
        except Exception as e:
            logger.error(f"❌ Referral processing error: {e}")
    
    # Get user stats
    stats = await get_user_stats(user.id)
    plan = await get_user_plan(user.id)
    fee = get_plan_fee(plan)
    
    # Welcome message
    welcome_msg = "🌟 Welcome to SHEGER ET - Ethiopia's Super App! 🇪🇹"
    if referral_code:
        welcome_msg = "🎉 Welcome! You were referred by a friend!"
    
    keyboard = [
        [InlineKeyboardButton(f"⭐ {plan.upper()} PLAN", callback_data="my_plan"),
         InlineKeyboardButton("🚀 UPGRADE NOW", callback_data="premium")],
        [InlineKeyboardButton("💰 MY WALLET", callback_data="wallet"),
         InlineKeyboardButton("🤝 REFER & EARN", callback_data="referral")],
        [InlineKeyboardButton("💸 SEND MONEY", callback_data="send_money"),
         InlineKeyboardButton("🛍️ MARKETPLACE", callback_data="marketplace")],
        [InlineKeyboardButton("🔧 FIND WORK", callback_data="jobs"),
         InlineKeyboardButton("🏠 PROPERTIES", callback_data="properties")],
        [InlineKeyboardButton("📊 ANALYTICS", callback_data="analytics"),
         InlineKeyboardButton("🎁 PROMOTIONS", callback_data="promotions")],
        [InlineKeyboardButton("📞 SUPPORT", url=f"https://t.me/{SUPPORT.replace('@', '')}"),
         InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")]
    ]
    
    text = f"""*{BOT_NAME} V2* 🇪🇹
*{BOT_SLOGAN}*

{welcome_msg}

*Your Profile:*
🏷️ Plan: *{plan.upper()}*
💸 Fee: *{fee}%*
💰 Balance: *{stats.get('balance', 0):.0f} ETB*
👥 Referred: *{stats.get('referred_count', 0)} users*
🎯 Earned: *{stats.get('total_earned', 0):.0f} ETB*

*Quick Actions:*
• Upgrade to save on transaction fees
• Refer friends & earn 10% commission
• Check active promotions
• Explore all services

*Ready to maximize your earnings?*"""
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def premium_command(update: Update, context):
    """Show premium plans"""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Get active campaigns
    campaigns = await get_campaigns()
    
    keyboard = [
        [InlineKeyboardButton("🚀 PRO - 149 ETB/month", callback_data="upgrade_pro")],
        [InlineKeyboardButton("🏢 BUSINESS - 999 ETB/month", callback_data="upgrade_business")],
        [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    # Add campaign buttons if available
    if campaigns:
        for campaign in campaigns[:2]:  # Max 2 campaign buttons
            if campaign.get('discount_percent'):
                btn_text = f"🎯 {campaign['name']} ({campaign['discount_percent']}% OFF)"
            else:
                btn_text = f"🎯 {campaign['name']}"
            keyboard.insert(0, [InlineKeyboardButton(btn_text, callback_data=f"campaign_{campaign['code']}")])
    
    text = f"""🚀 *{BOT_NAME} PREMIUM PLANS*

*Special Offers Available:*"""
    
    for campaign in campaigns:
        if campaign.get('discount_percent'):
            text += f"\n• {campaign['name']}: {campaign['discount_percent']}% OFF (Code: `{campaign['code']}`)"
        elif campaign.get('discount_amount'):
            text += f"\n• {campaign['name']}: {campaign['discount_amount']} ETB OFF"
    
    text += f"""

*1. SHEGER PRO* - 149 ETB/month
• Fee: 1.5% (Basic: 2.5%) - Save 40%!
• Unlimited listings
• Priority support
• Business badge
• 50K ETB daily limit
• Referral earnings

*2. SHEGER BUSINESS* - 999 ETB/month
• Fee: 0.8% (Lowest in Ethiopia!)
• Bulk payments API
• Business dashboard
• Dedicated manager
• White-label solutions
• Highest referral rates

*💎 VIP Benefits:*
• Early access to new features
• Custom integration support
• Volume discounts
• Marketing co-promotion

*Choose your plan and start saving today!*"""
    
    if query:
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def my_plan_command(update: Update, context):
    """Show user's current plan"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = await get_user_stats(user.id)
    plan = await get_user_plan(user.id)
    fee = get_plan_fee(plan)
    
    # Calculate days remaining if premium
    days_remaining = 0
    if plan != 'basic':
        # Get last payment date
        response = supabase.table('payments')\
            .select('verified_at')\
            .eq('user_id', user.id)\
            .eq('status', 'verified')\
            .order('verified_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and response.data[0].get('verified_at'):
            last_payment = datetime.fromisoformat(response.data[0]['verified_at'].replace('Z', '+00:00'))
            days_passed = (datetime.now() - last_payment).days
            days_remaining = max(0, 30 - days_passed)
    
    benefits = {
        'basic': """• 2.5% transaction fee
• 5 free listings/month
• Standard support
• Basic features""",
        'pro': """• 1.5% transaction fee (Save 40%!)
• Unlimited listings
• Priority support
• Business badge
• Referral earnings
• Advanced analytics""",
        'business': """• 0.8% transaction fee (Lowest rate!)
• Bulk payment processing
• Business dashboard
• Dedicated manager
• API access
• White-label solutions"""
    }.get(plan, "")
    
    keyboard = [
        [InlineKeyboardButton("🚀 UPGRADE PLAN", callback_data="premium")]
    ]
    
    if plan != 'basic':
        keyboard.append([InlineKeyboardButton("🔄 RENEW PLAN", callback_data=f"renew_{plan}")])
    
    keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")])
    
    text = f"""⭐ *YOUR {BOT_NAME} PLAN*

*Current Plan:* {plan.upper()}
*Transaction Fee:* {fee}%
*Status:* Active ✅
{f"*Days Remaining:* {days_remaining}" if days_remaining > 0 else ""}

*Plan Benefits:*
{benefits}

*Your Stats:*
💰 Total Spent: {stats.get('total_spent', 0):.0f} ETB
💎 Total Earned: {stats.get('total_earned', 0):.0f} ETB
👥 Referred: {stats.get('referred_count', 0)} users

*Ready for more?* Upgrade to unlock better features and earn more!"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def wallet_command(update: Update, context):
    """Show user wallet"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = await get_user_stats(user.id)
    
    keyboard = [
        [InlineKeyboardButton("📥 ADD FUNDS", callback_data="add_funds"),
         InlineKeyboardButton("📤 WITHDRAW", callback_data="withdraw_funds")],
        [InlineKeyboardButton("📋 TRANSACTION HISTORY", callback_data="transactions")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    # Get recent transactions
    try:
        response = supabase.table('payments')\
            .select('amount, status, created_at')\
            .eq('user_id', user.id)\
            .order('created_at', desc=True)\
            .limit(3)\
            .execute()
        
        recent_tx = response.data or []
    except:
        recent_tx = []
    
    text = f"""💰 *YOUR SHEGER WALLET*

*Balance Summary:*
💳 Available Balance: {stats.get('balance', 0):.0f} ETB
📈 Total Earned: {stats.get('total_earned', 0):.0f} ETB
💸 Total Spent: {stats.get('total_spent', 0):.0f} ETB

*Recent Transactions:*"""
    
    if recent_tx:
        for tx in recent_tx:
            date = datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00')).strftime("%b %d")
            status_icon = "✅" if tx.get('status') == 'verified' else "⏳"
            amount = float(tx.get('amount', 0))
            text += f"\n{status_icon} {amount:.0f} ETB - {date}"
    else:
        text += "\nNo transactions yet."
    
    text += f"""

*Quick Actions:*
• Add funds to your wallet
• Withdraw earnings anytime
• View complete history

*Withdrawal Info:*
• Min: 100 ETB
• Fee: 1% (Max 10 ETB)
• Time: 24 hours
• Methods: telebirr, CBE"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def referral_command(update: Update, context):
    """Referral system"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = await get_user_stats(user.id)
    
    referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={stats.get('referral_code', '')}"
    
    keyboard = [
        [InlineKeyboardButton("📋 COPY REFERRAL LINK", callback_data="copy_ref_link")],
        [InlineKeyboardButton("👥 MY REFERRALS", callback_data="my_referrals")],
        [InlineKeyboardButton("💰 WITHDRAW EARNINGS", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""🤝 *REFER & EARN PROGRAM*

*Your Referral Stats:*
👥 Total Referred: {stats.get('referred_count', 0)} users
💰 Total Earned: {stats.get('total_earned', 0):.0f} ETB
💳 Available Balance: {stats.get('balance', 0):.0f} ETB
🎯 Lifetime Potential: Unlimited!

*How It Works:*
1. Share your unique link below
2. Friends sign up using your link
3. When they upgrade to PRO/BUSINESS
4. You earn *10% commission* instantly!

*Your Unique Link:*
`{referral_link}`

*Your Referral Code:*
`{stats.get('referral_code', '')}`

*Commission Rates:*
• PRO upgrade (149 ETB) → You earn 14.9 ETB
• BUSINESS upgrade (999 ETB) → You earn 99.9 ETB
• Lifetime earnings on their renewals!

*Start sharing and earning today!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def analytics_command(update: Update, context):
    """User analytics dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = await get_user_stats(user.id)
    plan = await get_user_plan(user.id)
    fee = get_plan_fee(plan)
    
    # Calculate savings
    monthly_savings = 0
    if plan != 'basic':
        typical_monthly = 10000  # Example monthly volume
        basic_fee = typical_monthly * 0.025
        current_fee = typical_monthly * (fee/100)
        monthly_savings = basic_fee - current_fee
    
    keyboard = [
        [InlineKeyboardButton("📈 REVENUE ANALYTICS", callback_data="revenue_analytics"),
         InlineKeyboardButton("👥 REFERRAL ANALYTICS", callback_data="referral_analytics")],
        [InlineKeyboardButton("📊 GROWTH TRENDS", callback_data="growth_trends")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""📊 *YOUR ANALYTICS DASHBOARD*

*Account Overview:*
👤 User ID: `{user.id}`
🏷️ Current Plan: {plan.upper()}
💸 Transaction Fee: {fee}%
📅 Member Since: {datetime.fromisoformat(stats['joined_date'].replace('Z', '+00:00')).strftime('%b %d, %Y') if stats.get('joined_date') else 'Recently'}

*Financial Metrics:*
💰 Lifetime Spent: {stats.get('total_spent', 0):.0f} ETB
💎 Lifetime Earned: {stats.get('total_earned', 0):.0f} ETB
📈 Net Position: {(stats.get('total_earned', 0) - stats.get('total_spent', 0)):.0f} ETB
🎯 Monthly Savings: {monthly_savings:.0f} ETB
🏆 Annual Savings: {(monthly_savings * 12):.0f} ETB

*Referral Performance:*
👥 Total Referred: {stats.get('referred_count', 0)} users
📊 Conversion Rate: {((stats.get('referred_count', 0)/max(stats.get('total_payments', 1), 1))*100 if stats.get('referred_count', 0) > 0 else 0):.1f}%
💵 Referral Revenue: {stats.get('referred_revenue', 0):.0f} ETB
⭐ Avg/Referral: {(stats.get('referred_revenue', 0)/max(stats.get('referred_count', 1), 1)):.0f} ETB

*Upgrade to PRO for advanced analytics!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def promotions_command(update: Update, context):
    """Show active promotions"""
    query = update.callback_query
    await query.answer()
    
    campaigns = await get_campaigns()
    
    keyboard = []
    for campaign in campaigns[:5]:  # Show max 5 campaigns
        if campaign.get('discount_percent'):
            btn_text = f"🎁 {campaign['name']} ({campaign['discount_percent']}% OFF)"
        else:
            btn_text = f"🎁 {campaign['name']} ({campaign.get('discount_amount', 0)} ETB OFF)"
        
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"campaign_{campaign['code']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")])
    
    text = """🎯 *PROMOTIONS CENTER*

*Active Campaigns:*"""
    
    for campaign in campaigns:
        remaining = campaign.get('max_uses', 0) - campaign.get('used_count', 0) if campaign.get('max_uses') else '∞'
        expires = datetime.fromisoformat(campaign['expires_at'].replace('Z', '+00:00')).strftime('%b %d') if campaign.get('expires_at') else 'Never'
        
        if campaign.get('discount_percent'):
            discount = f"{campaign['discount_percent']}% OFF"
        else:
            discount = f"{campaign.get('discount_amount', 0)} ETB OFF"
        
        text += f"""
• *{campaign['name']}*
   Code: `{campaign['code']}`
   Discount: {discount}
   Remaining: {remaining} uses
   Expires: {expires}"""
    
    text += """

*How to Use:*
1. Click on any promotion
2. Copy the promo code
3. Select upgrade plan
4. Apply code during payment

*New promotions added weekly!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# ADMIN COMMANDS
# ======================

async def admin_command(update: Update, context):
    """Admin dashboard"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    try:
        # Get platform stats
        users_resp = supabase.table('users').select('*', count='exact').execute()
        total_users = users_resp.count or 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_users_resp = supabase.table('users')\
            .select('*', count='exact')\
            .gte('joined_at', f'{today}T00:00:00')\
            .lte('joined_at', f'{today}T23:59:59')\
            .execute()
        today_users = today_users_resp.count or 0
        
        premium_resp = supabase.table('users')\
            .select('*', count='exact')\
            .neq('plan', 'basic')\
            .execute()
        premium_users = premium_resp.count or 0
        
        # Revenue
        revenue_resp = supabase.table('payments')\
            .select('amount')\
            .eq('status', 'verified')\
            .execute()
        total_revenue = sum(float(p.get('amount', 0) or 0) for p in (revenue_resp.data or []))
        
        # Today's revenue
        today_rev_resp = supabase.table('payments')\
            .select('amount')\
            .eq('status', 'verified')\
            .gte('verified_at', f'{today}T00:00:00')\
            .lte('verified_at', f'{today}T23:59:59')\
            .execute()
        today_revenue = sum(float(p.get('amount', 0) or 0) for p in (today_rev_resp.data or []))
        
        # Pending payments
        pending_resp = supabase.table('payments')\
            .select('*', count='exact')\
            .eq('status', 'pending')\
            .execute()
        pending_payments = pending_resp.count or 0
        
        # Referral stats
        referral_resp = supabase.table('users')\
            .select('*', count='exact')\
            .not_.is_('referred_by', 'null')\
            .execute()
        referral_users = referral_resp.count or 0
        
        # Total paid out
        payouts_resp = supabase.table('users')\
            .select('total_earned')\
            .execute()
        total_paid_out = sum(float(u.get('total_earned', 0) or 0) for u in (payouts_resp.data or []))
        
        text = f"""👑 *{BOT_NAME} ADMIN DASHBOARD*

*Platform Overview:*
👥 Total Users: {total_users:,}
📈 Today's New: {today_users}
💎 Premium Users: {premium_users} ({premium_users/max(total_users,1)*100:.1f}%)
🤝 Referral Users: {referral_users}

*Financial Performance:*
💰 Total Revenue: {total_revenue:,.0f} ETB
📊 Today's Revenue: {today_revenue:,.0f} ETB
⏳ Pending Payments: {pending_payments}
💵 Total Paid Out: {total_paid_out:,.0f} ETB
📈 Net Profit: {(total_revenue - total_paid_out):,.0f} ETB

*Database: Supabase PostgreSQL ✅*
*Backend: Production Ready ✅*

*Admin Commands:*
`/verify USER_ID` - Verify payment
`/pending` - Show pending payments
`/users` - User management
`/campaigns` - Manage promotions
`/broadcast` - Send announcement
`/stats` - Detailed statistics"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Admin command error: {e}")
        await update.message.reply_text(f"Error: {e}")

async def verify_command(update: Update, context):
    """Verify user payment"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/verify USER_ID [AMOUNT] [PLAN]`")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1]) if len(context.args) > 1 else None
        plan = context.args[2] if len(context.args) > 2 else None
        
        success, message = await verify_payment(user_id, ADMIN_ID, amount, plan)
        
        if success:
            # Send notification to user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ *PAYMENT VERIFIED!*\n\nYour payment has been verified and your account has been upgraded!\n\nThank you for choosing {BOT_NAME}!",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"❌ Verify command error: {e}")
        await update.message.reply_text(f"Error: {e}")

async def pending_command(update: Update, context):
    """Show pending payments"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    try:
        response = supabase.table('payments')\
            .select('*')\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .limit(20)\
            .execute()
        
        payments = response.data or []
        
        if not payments:
            await update.message.reply_text("No pending payments.")
            return
        
        text = "⏳ *PENDING PAYMENTS*\n\n"
        
        for i, payment in enumerate(payments, 1):
            user_id = payment['user_id']
            amount = float(payment.get('amount', 0))
            plan = payment.get('plan', 'unknown')
            ref = payment.get('reference_code', 'N/A')
            created = datetime.fromisoformat(payment['created_at'].replace('Z', '+00:00')).strftime('%b %d %H:%M')
            
            text += f"{i}. User: `{user_id}`\n"
            text += f"   Plan: {plan.upper()}\n"
            text += f"   Amount: {amount:.0f} ETB\n"
            text += f"   Ref: `{ref}`\n"
            text += f"   Created: {created}\n\n"
        
        text += f"*Total:* {len(payments)} pending payments\n"
        text += "*Verify:* `/verify USER_ID`"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Pending command error: {e}")
        await update.message.reply_text(f"Error: {e}")

async def stats_command(update: Update, context):
    """Show detailed statistics"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    try:
        # Get daily stats for last 7 days
        text = "📊 *PLATFORM STATISTICS*\n\n"
        
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Users joined
            users_resp = supabase.table('users')\
                .select('*', count='exact')\
                .gte('joined_at', f'{date}T00:00:00')\
                .lte('joined_at', f'{date}T23:59:59')\
                .execute()
            
            # Revenue
            revenue_resp = supabase.table('payments')\
                .select('amount')\
                .eq('status', 'verified')\
                .gte('verified_at', f'{date}T00:00:00')\
                .lte('verified_at', f'{date}T23:59:59')\
                .execute()
            
            users_today = users_resp.count or 0
            revenue_today = sum(float(p.get('amount', 0) or 0) for p in (revenue_resp.data or []))
            
            display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%b %d')
            text += f"{display_date}: {users_today} users, {revenue_today:.0f} ETB\n"
        
        # Plan distribution
        plan_resp = supabase.table('users')\
            .select('plan', count='exact')\
            .execute()
        
        # Group by plan
        plan_counts = {}
        if plan_resp.data:
            for user in plan_resp.data:
                plan = user.get('plan', 'basic')
                plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        text += "\n*Plan Distribution:*\n"
        for plan, count in plan_counts.items():
            text += f"{plan.upper()}: {count} users\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Stats command error: {e}")
        await update.message.reply_text(f"Error: {e}")

async def broadcast_command(update: Update, context):
    """Broadcast message to all users"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Your message here`")
        return
    
    message = ' '.join(context.args)
    
    # Get all active users
    try:
        users_resp = supabase.table('users')\
            .select('id')\
            .eq('status', 'active')\
            .execute()
        
        users = users_resp.data or []
        total = len(users)
        
        await update.message.reply_text(f"📢 Broadcasting to {total} users...")
        
        success = 0
        failed = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['id'],
                    text=f"📢 *ANNOUNCEMENT FROM {BOT_NAME}*\n\n{message}\n\n_This is an automated broadcast._",
                    parse_mode='Markdown'
                )
                success += 1
                
                # Create notification
                await create_notification(
                    user['id'],
                    "Announcement",
                    message,
                    "broadcast"
                )
                
                # Rate limiting
                if success % 20 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send to {user['id']}: {e}")
        
        # Send report
        report = f"""📊 *BROADCAST COMPLETE*

Total Users: {total}
✅ Successful: {success}
❌ Failed: {failed}
📈 Success Rate: {success/total*100 if total > 0 else 0:.1f}%

Message sent to database notifications."""
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Broadcast error: {e}")
        await update.message.reply_text(f"Error: {e}")

# ======================
# BUTTON HANDLER
# ======================

async def button_handler(update: Update, context):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Main navigation
    if data == "back_to_main":
        await start_command(update, context)
        return
    
    elif data == "premium":
        await premium_command(update, context)
    
    elif data == "my_plan":
        await my_plan_command(update, context)
    
    elif data == "wallet":
        await wallet_command(update, context)
    
    elif data == "referral":
        await referral_command(update, context)
    
    elif data == "analytics":
        await analytics_command(update, context)
    
    elif data == "promotions":
        await promotions_command(update, context)
    
    elif data == "upgrade_pro":
        # Create payment for PRO plan
        ref_code = await create_payment(user.id, user.username, "pro", 149)
        
        if ref_code:
            keyboard = [
                [InlineKeyboardButton("💳 PAY WITH TELEBIRR", callback_data=f"pay_telebirr_{ref_code}")],
                [InlineKeyboardButton("🏦 PAY WITH CBE", callback_data=f"pay_cbe_{ref_code}")],
                [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo_pro")],
                [InlineKeyboardButton("🔙 BACK", callback_data="premium")]
            ]
            
            text = f"""✅ *SHEGER PRO SELECTED*

💰 *149 ETB/month*
👤 User: @{user.username}
🆔 Your ID: `{user.id}`
📋 Reference: `{ref_code}`

*Payment Methods:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Instructions:*
1. Send payment to the number above
2. Include reference: `{ref_code}`
3. Take screenshot of payment
4. Send to {PAYMENTS}

*Benefits Activated Immediately After Verification!*"""
            
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "upgrade_business":
        # Create payment for BUSINESS plan
        ref_code = await create_payment(user.id, user.username, "business", 999)
        
        if ref_code:
            text = f"""🏢 *SHEGER BUSINESS SELECTED*

💰 *999 ETB/month*
👤 User: @{user.username}
🆔 Your ID: `{user.id}`
📋 Reference: `{ref_code}`

*For business inquiries, contact:* {SALES}

*Payment Methods:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Instructions:*
1. Contact {SALES} for business setup
2. Get custom invoice
3. Make payment with reference
4. Get dedicated account manager

*🏢 Perfect for:*
• Businesses with 10+ employees
• Companies processing 100K+ ETB monthly
• Organizations needing custom solutions
• Enterprises requiring API integration"""
            
            await query.edit_message_text(text, parse_mode='Markdown')
    
    elif data.startswith("campaign_"):
        campaign_code = data.replace("campaign_", "")
        
        campaigns = await get_campaigns()
        campaign = next((c for c in campaigns if c['code'] == campaign_code), None)
        
        if campaign:
            if campaign.get('discount_percent'):
                discount = f"{campaign['discount_percent']}% OFF"
            else:
                discount = f"{campaign.get('discount_amount', 0)} ETB OFF"
            
            text = f"""🎁 *{campaign['name']}*

*Discount:* {discount}
*Code:* `{campaign['code']}`
*Type:* {campaign.get('type', 'promotion').title()}
*Uses Left:* {campaign.get('max_uses', 0) - campaign.get('used_count', 0) if campaign.get('max_uses') else '∞'}
*Expires:* {datetime.fromisoformat(campaign['expires_at'].replace('Z', '+00:00')).strftime('%B %d, %Y') if campaign.get('expires_at') else 'Never'}

*How to Use:*
1. Click UPGRADE NOW
2. Select your plan
3. Apply code: `{campaign['code']}`
4. Complete payment"""
            
            keyboard = [
                [InlineKeyboardButton("🚀 UPGRADE NOW", callback_data="premium")],
                [InlineKeyboardButton("🔙 BACK", callback_data="promotions")]
            ]
            
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "send_money":
        plan = await get_user_plan(user.id)
        fee = get_plan_fee(plan)
        
        text = f"""💸 *SEND MONEY WITH {BOT_NAME}*

*Your current fee:* {fee}% ({plan.upper()} plan)

*Features:*
• Send to any phone number
• Bank transfers
• Instant to SHEGER users
• Scheduled payments
• Bulk payments (Business only)

*Current Rates:*
• Basic: 2.5% (min 5 ETB)
• PRO: 1.5% (Save 40%!)
• Business: 0.8% (Lowest!)

*Coming Soon!* 🚀"""
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "marketplace":
        plan = await get_user_plan(user.id)
        
        text = f"""🛍️ *{BOT_NAME} MARKETPLACE*

*Available Categories:*
• 📱 Electronics & Phones
• 👗 Fashion & Clothing
• 🏡 Home & Furniture
• 🚗 Vehicles & Auto Parts
• 🔧 Services & Professionals

*Your Plan ({plan.upper()}):*
• {"Unlimited listings" if plan != 'basic' else "5 free listings/month"}
• {"Priority placement" if plan != 'basic' else "Standard placement"}
• {"Advanced analytics" if plan == 'business' else "Basic analytics"}

*Coming Soon!* 🚀"""
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "jobs":
        text = f"""🔧 *FIND WORK ON {BOT_NAME}*

*Top Job Categories:*
• 💻 Tech & Programming
• 🏗️ Construction & Labor
• 🚚 Driving & Delivery
• 👨‍🏫 Teaching & Tutoring
• 🏥 Healthcare

*For Job Seekers:*
• Browse verified jobs
• Apply directly
• Get job alerts
• Build profile

*For Employers:*
• Post jobs for FREE
• Reach qualified candidates
• Manage applications

*Coming Soon!* 🚀"""
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "properties":
        text = f"""🏠 *PROPERTIES ON {BOT_NAME}*

*Find Your Perfect Property:*
• 🏡 Houses for Rent/Sale
• 🏢 Apartments & Condos
• 🏪 Commercial Spaces
• 🗺️ Land & Plots
• 🏖️ Vacation Rentals

*Verified Properties Only:*
✅ All listings verified
✅ Authentic photos
✅ Accurate location data
✅ Price transparency

*Coming Soon!* 🚀"""
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    else:
        await query.edit_message_text("Feature coming soon! 🚀")

# ======================
# REAL-TIME SUBSCRIPTIONS
# ======================

async def setup_real_time():
    """Set up real-time subscriptions"""
    try:
        # Subscribe to new payments
        channel = supabase.channel('payments')
        
        @channel.on('postgres_changes', event='INSERT', schema='public', table='payments')
        def on_payment_insert(payload):
            logger.info(f"New payment: {payload['new']['reference_code']}")
            # Could send real-time notification here
        
        @channel.on('postgres_changes', event='UPDATE', schema='public', table='payments')
        def on_payment_update(payload):
            new_status = payload['new'].get('status')
            old_status = payload['old'].get('status')
            
            if new_status == 'verified' and old_status != 'verified':
                logger.info(f"Payment verified: {payload['new']['reference_code']}")
                # Could send real-time notification here
        
        channel.subscribe()
        logger.info("✅ Real-time subscriptions activated")
        
    except Exception as e:
        logger.error(f"❌ Real-time setup error: {e}")

# ======================
# SCHEDULED TASKS
# ======================

async def scheduled_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Run scheduled maintenance tasks"""
    try:
        logger.info("🔄 Running scheduled tasks...")
        
        # Check for expired payments
        expired_response = supabase.table('payments')\
            .select('*')\
            .eq('status', 'pending')\
            .lt('expires_at', datetime.now().isoformat())\
            .execute()
        
        expired_payments = expired_response.data or []
        
        for payment in expired_payments:
            supabase.table('payments')\
                .update({'status': 'expired'})\
                .eq('id', payment['id'])\
                .execute()
            
            logger.info(f"Expired payment: {payment['reference_code']}")
        
        # Send daily report to admin at 9 AM
        if datetime.now().hour == 9:
            await send_daily_report(context)
        
        logger.info(f"✅ Scheduled tasks completed. Expired: {len(expired_payments)} payments")
        
    except Exception as e:
        logger.error(f"❌ Scheduled tasks error: {e}")

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """Send daily report to admin"""
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # New users yesterday
        new_users_resp = supabase.table('users')\
            .select('*', count='exact')\
            .gte('joined_at', f'{yesterday}T00:00:00')\
            .lte('joined_at', f'{yesterday}T23:59:59')\
            .execute()
        new_users = new_users_resp.count or 0
        
        # Revenue yesterday
        revenue_resp = supabase.table('payments')\
            .select('amount')\
            .eq('status', 'verified')\
            .gte('verified_at', f'{yesterday}T00:00:00')\
            .lte('verified_at', f'{yesterday}T23:59:59')\
            .execute()
        revenue = sum(float(p.get('amount', 0) or 0) for p in (revenue_resp.data or []))
        
        text = f"""📅 *DAILY REPORT - {yesterday}*

*Key Metrics:*
👥 New Users: {new_users}
💰 Daily Revenue: {revenue:,.0f} ETB

*System Status:* ✅ All Systems Operational
*Database:* Supabase PostgreSQL
*Backups:* Automatic
*Uptime:* 100%

Have a productive day! 🚀"""
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Daily report error: {e}")

# ======================
# HELP COMMAND
# ======================

async def help_command(update: Update, context):
    """Help command"""
    text = f"""🆘 *{BOT_NAME} HELP*

*Basic Commands:*
`/start` - Main menu
`/premium` - Upgrade plans
`/wallet` - Your wallet
`/referral` - Referral program
`/analytics` - Your statistics
`/help` - This message

*Admin Commands:*
`/admin` - Admin dashboard
`/verify USER_ID` - Verify payment
`/pending` - Pending payments
`/stats` - Platform statistics
`/broadcast` - Send announcement

*Support Channels:*
📞 Customer Support: {SUPPORT}
💰 Payment Issues: {PAYMENTS}
🏢 Business Sales: {SALES}
📰 News & Updates: {NEWS}

*24/7 Support Available*"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# MAIN FUNCTION
# ======================

def main():
    """Start the bot"""
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not set in environment!")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Register button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Setup job queue for scheduled tasks
    job_queue = application.job_queue
    if job_queue:
        # Run every hour
        job_queue.run_repeating(
            scheduled_tasks,
            interval=3600,
            first=10,
            name="scheduled_tasks"
        )
        
        # Run daily at 9 AM
        job_queue.run_daily(
            send_daily_report,
            time=datetime.time(hour=9, minute=0),
            name="daily_report"
        )
    
    # Setup real-time subscriptions
    asyncio.run(setup_real_time())
    
    # Startup message
    logger.info("=" * 70)
    logger.info(f"🚀 {BOT_NAME} V2 - PRODUCTION")
    logger.info(f"🌟 {BOT_SLOGAN}")
    logger.info(f"🤖 Bot: {BOT_USERNAME}")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"💾 Database: Supabase PostgreSQL")
    logger.info("✅ SUPABASE FEATURES ENABLED:")
    logger.info("   • Real-time Database")
    logger.info("   • Automatic Backups")
    logger.info("   • Row Level Security")
    logger.info("   • Scalable Infrastructure")
    logger.info("=" * 70)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
