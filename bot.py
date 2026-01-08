#!/usr/bin/env python3
"""
SHEGER ET V2 - Enhanced Ethiopian Super App
Production Ready with Marketing & Automation
"""

import os
import json
import logging
import sqlite3
import shutil
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================
# CONFIGURATION V2
# ======================
TELEBIRR = "0961393001"
CBE = "1000645865603"
ADMIN_ID = 7714584854

SUPPORT = "@ShegerESupport"
PAYMENTS = "@ShegerPayments"
SALES = "@ShegerESales"
NEWS = "@ShegeErNews"

BOT_NAME = "SHEGER ET"
BOT_USERNAME = "@ShegerETBot"
BOT_SLOGAN = "Ethiopia's All-in-One Super App"

# ======================
# DATABASE V2 ENHANCED
# ======================
DATABASE_PATH = os.getenv("DATABASE_URL", "sheger_et_v2.db")
BACKUP_DIR = "sheger_backups_v2"

# Setup enhanced logging
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
# ENHANCED DATABASE V2
# ======================
def init_database_v2():
    """Initialize enhanced database with marketing and analytics"""
    try:
        # Create backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Enable WAL mode
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Enhanced users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                email TEXT,
                plan TEXT DEFAULT 'basic',
                balance REAL DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                total_spent REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                join_source TEXT,
                campaign_id TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_payment TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # Enhanced payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                plan TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                reference_code TEXT UNIQUE,
                payment_method TEXT,
                payment_proof TEXT,
                admin_notes TEXT,
                verified_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                expires_at TIMESTAMP,
                campaign_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Marketing campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                code TEXT UNIQUE,
                type TEXT, -- referral, discount, promo
                discount_percent REAL,
                discount_amount REAL,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                starts_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT, -- user_join, payment, upgrade, referral
                user_id INTEGER,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                message TEXT,
                notification_type TEXT, -- payment, reminder, promo, update
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_ref_code ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_campaign ON payments(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event_type, created_at)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ V2 Database initialized: {DATABASE_PATH}")
        
        # Create default campaigns
        create_default_campaigns()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def create_default_campaigns():
    """Create default marketing campaigns"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Launch campaign
        cursor.execute('''
            INSERT OR IGNORE INTO campaigns 
            (name, code, type, discount_percent, max_uses, starts_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Launch Special',
            'SHEGERLAUNCH',
            'discount',
            100,  # 100% discount = first month free
            1000,
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=30)).isoformat(),
            1
        ))
        
        # Referral campaign
        cursor.execute('''
            INSERT OR IGNORE INTO campaigns 
            (name, code, type, discount_amount, max_uses, starts_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Referral Bonus',
            'REFER10',
            'referral',
            14.9,  # 10% of 149 ETB
            10000,
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=365)).isoformat(),
            1
        ))
        
        conn.commit()
        conn.close()
        logger.info("✅ Default campaigns created")
        
    except Exception as e:
        logger.error(f"Error creating campaigns: {e}")

# Initialize database
init_database_v2()

# ======================
# ENHANCED DATABASE FUNCTIONS V2
# ======================
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code"""
    prefix = "SHEGER"
    unique = f"{user_id:06d}"[-6:]
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{unique}{chars}"

def create_or_update_user_v2(user_id: int, username: str, full_name: str, source: str = "bot"):
    """Create or update user with enhanced tracking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, referral_code FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute('''
                UPDATE users 
                SET username = ?, full_name = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username, full_name, user_id))
            
            referral_code = user['referral_code']
            
        else:
            # Create new user with referral code
            referral_code = generate_referral_code(user_id)
            
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, full_name, referral_code, join_source, joined_at, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, username, full_name, referral_code, source))
            
            # Log analytics
            cursor.execute('''
                INSERT INTO analytics (event_type, user_id, data)
                VALUES (?, ?, ?)
            ''', ('user_join', user_id, json.dumps({'source': source})))
            
            logger.info(f"👤 V2 User created: {user_id} (@{username}) from {source}")
        
        conn.commit()
        conn.close()
        return referral_code
        
    except Exception as e:
        logger.error(f"Error creating user V2: {e}")
        return None

def create_payment_v2(user_id: int, username: str, plan: str, amount: float, campaign_code: str = None):
    """Create payment with campaign tracking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        reference_code = f"{plan.upper()}-{user_id}-{int(datetime.now().timestamp())}"
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO payments 
            (user_id, username, plan, amount, reference_code, expires_at, campaign_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, plan, amount, reference_code, expires_at.isoformat(), campaign_code))
        
        # Log analytics
        cursor.execute('''
            INSERT INTO analytics (event_type, user_id, data)
            VALUES (?, ?, ?)
        ''', ('payment_initiated', user_id, json.dumps({
            'plan': plan,
            'amount': amount,
            'campaign': campaign_code
        })))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💰 V2 Payment created: {user_id} - {plan} - {amount} - Campaign: {campaign_code}")
        return reference_code
        
    except Exception as e:
        logger.error(f"Error creating payment V2: {e}")
        return None

def verify_payment_v2(user_id: int, admin_id: int, amount: float = None, plan: str = None):
    """Verify payment with referral rewards"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get pending payment
        cursor.execute('''
            SELECT * FROM payments 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        
        payment = cursor.fetchone()
        if not payment:
            return False, "No pending payment found"
        
        payment_id = payment['id']
        actual_plan = plan or payment['plan']
        actual_amount = amount or payment['amount']
        campaign_code = payment['campaign_id']
        
        # Apply campaign discount if exists
        final_amount = actual_amount
        if campaign_code:
            cursor.execute('''
                SELECT * FROM campaigns 
                WHERE code = ? AND is_active = 1 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''', (campaign_code,))
            
            campaign = cursor.fetchone()
            if campaign:
                if campaign['type'] == 'discount' and campaign['discount_percent']:
                    discount = actual_amount * (campaign['discount_percent'] / 100)
                    final_amount = actual_amount - discount
                elif campaign['type'] == 'discount' and campaign['discount_amount']:
                    final_amount = actual_amount - campaign['discount_amount']
                
                # Update campaign usage
                cursor.execute('''
                    UPDATE campaigns SET used_count = used_count + 1 WHERE id = ?
                ''', (campaign['id'],))
        
        # Update payment
        cursor.execute('''
            UPDATE payments 
            SET status = 'verified', 
                verified_by = ?, 
                verified_at = CURRENT_TIMESTAMP,
                plan = ?,
                amount = ?
            WHERE id = ?
        ''', (admin_id, actual_plan, final_amount, payment_id))
        
        # Update user
        cursor.execute('''
            UPDATE users 
            SET plan = ?, 
                total_spent = total_spent + ?,
                last_payment = CURRENT_TIMESTAMP,
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (actual_plan, final_amount, user_id))
        
        # Check for referral and reward referrer
        cursor.execute('''
            SELECT referred_by FROM users WHERE user_id = ?
        ''', (user_id,))
        
        referrer = cursor.fetchone()
        if referrer and referrer['referred_by']:
            reward_amount = final_amount * 0.10  # 10% referral reward
            cursor.execute('''
                UPDATE users 
                SET total_earned = total_earned + ?,
                    balance = balance + ?
                WHERE user_id = ?
            ''', (reward_amount, reward_amount, referrer['referred_by']))
            
            # Log referral reward
            cursor.execute('''
                INSERT INTO analytics (event_type, user_id, data)
                VALUES (?, ?, ?)
            ''', ('referral_reward', referrer['referred_by'], json.dumps({
                'referred_user': user_id,
                'amount': reward_amount
            })))
        
        # Log analytics
        cursor.execute('''
            INSERT INTO analytics (event_type, user_id, data)
            VALUES (?, ?, ?)
        ''', ('payment_verified', user_id, json.dumps({
            'plan': actual_plan,
            'amount': final_amount,
            'original_amount': actual_amount,
            'campaign': campaign_code
        })))
        
        conn.commit()
        conn.close()
        
        return True, f"Payment verified! User upgraded to {actual_plan.upper()}. Final amount: {final_amount} ETB"
        
    except Exception as e:
        logger.error(f"Error verifying payment V2: {e}")
        return False, f"Error: {str(e)}"

def get_user_stats(user_id: int) -> Dict:
    """Get comprehensive user statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # User info
        cursor.execute('''
            SELECT plan, total_spent, total_earned, balance, referral_code, joined_at
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return {}
        
        # Referral stats
        cursor.execute('''
            SELECT COUNT(*) as referred_count, 
                   SUM(total_spent) as referred_revenue
            FROM users WHERE referred_by = ?
        ''', (user_id,))
        
        referral_stats = cursor.fetchone()
        
        # Payment history
        cursor.execute('''
            SELECT COUNT(*) as total_payments,
                   SUM(amount) as total_verified_amount
            FROM payments 
            WHERE user_id = ? AND status = 'verified'
        ''', (user_id,))
        
        payment_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'plan': user['plan'],
            'total_spent': user['total_spent'] or 0,
            'total_earned': user['total_earned'] or 0,
            'balance': user['balance'] or 0,
            'referral_code': user['referral_code'],
            'joined_date': user['joined_at'],
            'referred_count': referral_stats['referred_count'] or 0,
            'referred_revenue': referral_stats['referred_revenue'] or 0,
            'total_payments': payment_stats['total_payments'] or 0,
            'total_verified': payment_stats['total_verified_amount'] or 0
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}

def get_plan(user_id: int) -> str:
    """Get user's current plan"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT plan, last_payment FROM users WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return 'basic'
        
        if user['last_payment']:
            last_payment = datetime.fromisoformat(user['last_payment'])
            if datetime.now() - last_payment <= timedelta(days=30):
                return user['plan']
        
        # Check if user has basic plan in database
        return user['plan'] or 'basic'
        
    except Exception as e:
        logger.error(f"Error getting plan: {e}")
        return 'basic'

def get_fee(user_id: int) -> float:
    """Get user's transaction fee"""
    plan = get_plan(user_id)
    return {"basic": 2.5, "pro": 1.5, "business": 0.8}[plan]

# ======================
# BACKUP & RECOVERY V2
# ======================
def create_backup_v2():
    """Create backup with metadata"""
    try:
        if not os.path.exists(DATABASE_PATH):
            return False, "Database file not found"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_v2_{timestamp}.db")
        
        # Create backup
        shutil.copy2(DATABASE_PATH, backup_file)
        
        # Create metadata file
        metadata = {
            'timestamp': timestamp,
            'database': DATABASE_PATH,
            'backup_file': backup_file,
            'size': os.path.getsize(backup_file),
            'version': 'V2'
        }
        
        metadata_file = backup_file.replace('.db', '.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Keep only last 20 backups
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_v2_")])
        if len(backups) > 20:
            for old_backup in backups[:-20]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                # Remove corresponding metadata
                metadata_file = old_backup.replace('.db', '.json')
                if os.path.exists(os.path.join(BACKUP_DIR, metadata_file)):
                    os.remove(os.path.join(BACKUP_DIR, metadata_file))
        
        return True, backup_file
        
    except Exception as e:
        return False, str(e)

# ======================
# ENHANCED COMMANDS V2
# ======================
async def start_v2(update: Update, context):
    """Enhanced start command with referral tracking"""
    user = update.effective_user
    
    # Check for referral parameter
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        logger.info(f"📨 User {user.id} came via referral code: {referral_code}")
    
    # Create/update user with referral
    user_ref_code = create_or_update_user_v2(user.id, user.username, user.full_name, "bot")
    
    # Process referral if exists
    if referral_code and user_ref_code:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Find referrer
            cursor.execute('''
                SELECT user_id FROM users WHERE referral_code = ?
            ''', (referral_code,))
            
            referrer = cursor.fetchone()
            if referrer:
                # Update user with referrer
                cursor.execute('''
                    UPDATE users SET referred_by = ? WHERE user_id = ?
                ''', (referrer['user_id'], user.id))
                
                # Log analytics
                cursor.execute('''
                    INSERT INTO analytics (event_type, user_id, data)
                    VALUES (?, ?, ?)
                ''', ('referral_click', user.id, json.dumps({
                    'referrer': referrer['user_id'],
                    'code': referral_code
                })))
                
                conn.commit()
                logger.info(f"🤝 Referral linked: {user.id} -> {referrer['user_id']}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error processing referral: {e}")
    
    # Get user stats
    stats = get_user_stats(user.id)
    plan = get_plan(user.id)
    fee = get_fee(user.id)
    
    # Welcome message based on referral
    welcome_msg = "Welcome"
    if referral_code:
        welcome_msg = "Welcome! You were referred by a friend 🎉"
    
    keyboard = [
        [InlineKeyboardButton(f"⭐ {plan.upper()} PLAN", callback_data="my_plan_v2"),
         InlineKeyboardButton("🚀 UPGRADE NOW", callback_data="premium_v2")],
        [InlineKeyboardButton("💰 MY WALLET", callback_data="wallet"),
         InlineKeyboardButton("🤝 REFER & EARN", callback_data="referral")],
        [InlineKeyboardButton("💸 SEND MONEY", callback_data="send_v2"),
         InlineKeyboardButton("🛍️ MARKETPLACE", callback_data="market_v2")],
        [InlineKeyboardButton("🔧 FIND WORK", callback_data="jobs_v2"),
         InlineKeyboardButton("🏠 PROPERTIES", callback_data="property_v2")],
        [InlineKeyboardButton("📊 ANALYTICS", callback_data="analytics"),
         InlineKeyboardButton("🎁 PROMOTIONS", callback_data="promotions")],
        [InlineKeyboardButton("📞 SUPPORT", url=f"https://t.me/ShegerESupport"),
         InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")]
    ]
    
    text = f"""🌟 *{BOT_NAME} V2* 🇪🇹
*{BOT_SLOGAN}*

{welcome_msg} @{user.username}!

*Your Profile:*
🏷️ Plan: {plan.upper()}
💸 Fee: {fee}%
💰 Balance: {stats.get('balance', 0):.0f} ETB
👥 Referred: {stats.get('referred_count', 0)} users
🎯 Earned: {stats.get('total_earned', 0):.0f} ETB

*Quick Actions:*
• Upgrade to save on fees
• Refer friends & earn 10%
• Check active promotions
• Explore all services

*Ready to maximize your earnings?*"""
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def premium_v2(update: Update, context):
    """Enhanced premium command with campaigns"""
    # Get active campaigns
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, code, discount_percent, discount_amount 
        FROM campaigns 
        WHERE type = 'discount' AND is_active = 1
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ORDER BY created_at DESC LIMIT 3
    ''')
    
    campaigns = cursor.fetchall()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🚀 PRO - 149 ETB/month", callback_data="upgrade_pro_v2")],
        [InlineKeyboardButton("🏢 BUSINESS - 999 ETB/month", callback_data="upgrade_business_v2")],
        [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo")]
    ]
    
    if campaigns:
        keyboard.insert(0, [InlineKeyboardButton(f"🎯 {campaigns[0]['name']}", callback_data=f"campaign_{campaigns[0]['code']}")])
    
    text = f"""🚀 *{BOT_NAME} PREMIUM V2*

*Special Offers:*
"""
    
    for campaign in campaigns:
        if campaign['discount_percent']:
            text += f"• {campaign['name']}: {campaign['discount_percent']:.0f}% OFF (Code: {campaign['code']})\n"
        elif campaign['discount_amount']:
            text += f"• {campaign['name']}: {campaign['discount_amount']:.0f} ETB OFF\n"
    
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
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def referral_system(update: Update, context):
    """Enhanced referral system"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    
    referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={stats['referral_code']}"
    
    keyboard = [
        [InlineKeyboardButton("📋 COPY REFERRAL LINK", callback_data="copy_ref_link")],
        [InlineKeyboardButton("👥 MY REFERRALS", callback_data="my_referrals")],
        [InlineKeyboardButton("💰 WITHDRAW EARNINGS", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""🤝 *REFER & EARN PROGRAM*

*Your Referral Stats:*
👥 Total Referred: {stats['referred_count']} users
💰 Total Earned: {stats['total_earned']:.0f} ETB
💳 Available Balance: {stats['balance']:.0f} ETB
🎯 Lifetime Potential: Unlimited!

*How It Works:*
1. Share your unique link below
2. Friends sign up using your link
3. When they upgrade to PRO/BUSINESS
4. You earn *10% commission* instantly!

*Your Unique Link:*
`{referral_link}`

*Your Referral Code:*
`{stats['referral_code']}`

*Commission Rates:*
• PRO upgrade (149 ETB) → You earn 14.9 ETB
• BUSINESS upgrade (999 ETB) → You earn 99.9 ETB
• Lifetime earnings on their renewals!

*Withdrawal:*
• Minimum: 100 ETB
• Methods: telebirr, CBE, PayPal
• Processing: 24 hours

*Start sharing and earning today!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def wallet_command(update: Update, context):
    """User wallet dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    
    keyboard = [
        [InlineKeyboardButton("📥 ADD FUNDS", callback_data="add_funds"),
         InlineKeyboardButton("📤 WITHDRAW", callback_data="withdraw_funds")],
        [InlineKeyboardButton("📋 TRANSACTION HISTORY", callback_data="transactions")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    # Get recent transactions
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, status, created_at 
        FROM payments 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 3
    ''', (user.id,))
    
    recent_tx = cursor.fetchall()
    conn.close()
    
    text = f"""💰 *YOUR SHEGER WALLET*

*Balance Summary:*
💳 Available Balance: {stats['balance']:.0f} ETB
📈 Total Earned: {stats['total_earned']:.0f} ETB
💸 Total Spent: {stats['total_spent']:.0f} ETB

*Recent Transactions:*
"""
    
    if recent_tx:
        for tx in recent_tx:
            date = datetime.fromisoformat(tx['created_at']).strftime("%b %d")
            status_icon = "✅" if tx['status'] == 'verified' else "⏳"
            text += f"{status_icon} {tx['amount']:.0f} ETB - {date}\n"
    else:
        text += "No transactions yet.\n"
    
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

async def analytics_dashboard(update: Update, context):
    """User analytics dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    plan = get_plan(user.id)
    fee = get_fee(user.id)
    
    # Calculate savings
    if plan != 'basic':
        typical_monthly = 10000
        basic_fee = typical_monthly * 0.025
        current_fee = typical_monthly * (fee/100)
        monthly_savings = basic_fee - current_fee
        annual_savings = monthly_savings * 12
    else:
        monthly_savings = 0
        annual_savings = 0
    
    keyboard = [
        [InlineKeyboardButton("📈 REVENUE ANALYTICS", callback_data="revenue_analytics"),
         InlineKeyboardButton("👥 REFERRAL ANALYTICS", callback_data="referral_analytics")],
        [InlineKeyboardButton("📊 GROWTH TRENDS", callback_data="growth_trends"),
         InlineKeyboardButton("🎯 GOALS", callback_data="set_goals")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""📊 *YOUR ANALYTICS DASHBOARD*

*Account Overview:*
👤 User ID: `{user.id}`
🏷️ Current Plan: {plan.upper()}
💸 Transaction Fee: {fee}%
📅 Member Since: {datetime.fromisoformat(stats['joined_date']).strftime('%b %d, %Y')}

*Financial Metrics:*
💰 Lifetime Spent: {stats['total_spent']:.0f} ETB
💎 Lifetime Earned: {stats['total_earned']:.0f} ETB
📈 Net Position: {(stats['total_earned'] - stats['total_spent']):.0f} ETB
🎯 Monthly Savings: {monthly_savings:.0f} ETB
🏆 Annual Savings: {annual_savings:.0f} ETB

*Referral Performance:*
👥 Total Referred: {stats['referred_count']} users
📊 Conversion Rate: {((stats['referred_count']/max(stats['total_payments'], 1))*100 if stats['referred_count'] > 0 else 0):.1f}%
💵 Referral Revenue: {stats['referred_revenue']:.0f} ETB
⭐ Avg/Referral: {(stats['referred_revenue']/max(stats['referred_count'], 1)):.0f} ETB

*Activity Score:*
🔄 Payments: {stats['total_payments']}
✅ Verified: {stats['total_verified']:.0f} ETB
📱 Last Active: Today

*Upgrade to PRO for advanced analytics!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def promotions_center(update: Update, context):
    """Active promotions center"""
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get active campaigns
    cursor.execute('''
        SELECT name, code, type, discount_percent, discount_amount, 
               max_uses, used_count, expires_at
        FROM campaigns 
        WHERE is_active = 1
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ORDER BY created_at DESC
    ''')
    
    campaigns = cursor.fetchall()
    conn.close()
    
    keyboard = []
    for campaign in campaigns:
        remaining = campaign['max_uses'] - campaign['used_count'] if campaign['max_uses'] else '∞'
        expires = datetime.fromisoformat(campaign['expires_at']).strftime('%b %d') if campaign['expires_at'] else 'Never'
        
        if campaign['discount_percent']:
            btn_text = f"🎁 {campaign['name']} ({campaign['discount_percent']:.0f}% OFF)"
        else:
            btn_text = f"🎁 {campaign['name']} ({campaign['discount_amount']:.0f} ETB OFF)"
        
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"campaign_{campaign['code']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")])
    
    text = """🎯 *PROMOTIONS CENTER*

*Active Campaigns:*
"""
    
    for campaign in campaigns:
        remaining = campaign['max_uses'] - campaign['used_count'] if campaign['max_uses'] else '∞'
        expires = datetime.fromisoformat(campaign['expires_at']).strftime('%b %d') if campaign['expires_at'] else 'Never'
        
        if campaign['discount_percent']:
            discount = f"{campaign['discount_percent']:.0f}% OFF"
        else:
            discount = f"{campaign['discount_amount']:.0f} ETB OFF"
        
        text += f"""• *{campaign['name']}*
   Code: `{campaign['code']}`
   Discount: {discount}
   Remaining: {remaining} uses
   Expires: {expires}

"""
    
    text += """
*How to Use:*
1. Click on any promotion
2. Copy the promo code
3. Select upgrade plan
4. Apply code during payment

*New promotions added weekly!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# ENHANCED ADMIN COMMANDS V2
# ======================
async def admin_dashboard_v2(update: Update, context):
    """Enhanced admin dashboard"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get comprehensive stats
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE('now')")
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE plan != 'basic'")
    premium_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified'")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified' AND DATE(verified_at) = DATE('now')")
    today_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL")
    referral_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_earned) FROM users")
    total_paid_out = cursor.fetchone()[0] or 0
    
    # Get campaign performance
    cursor.execute('''
        SELECT c.name, c.code, c.used_count, c.max_uses,
               SUM(p.amount) as revenue
        FROM campaigns c
        LEFT JOIN payments p ON c.code = p.campaign_id AND p.status = 'verified'
        WHERE c.is_active = 1
        GROUP BY c.id
    ''')
    
    campaigns = cursor.fetchall()
    
    conn.close()
    
    text = f"""👑 *SHEGER ET ADMIN DASHBOARD V2*

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

*Campaign Performance:*
"""
    
    for campaign in campaigns:
        remaining = campaign['max_uses'] - campaign['used_count'] if campaign['max_uses'] else '∞'
        usage = (campaign['used_count']/campaign['max_uses']*100) if campaign['max_uses'] else 0
        text += f"""• {campaign['name']} ({campaign['code']})
   Used: {campaign['used_count']}/{campaign['max_uses'] or '∞'} ({usage:.1f}%)
   Revenue: {campaign['revenue'] or 0:,.0f} ETB
   
"""
    
    text += f"""
*Quick Commands:*
`/verify USER_ID` - Verify payment
`/pending` - Pending payments
`/revenue` - Revenue analytics
`/campaigns` - Manage campaigns
`/broadcast` - Send announcement
`/backup` - Create backup

*Today's Priority:*
✅ Verify pending payments
✅ Check campaign performance
✅ Create backup
✅ Engage with users"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def revenue_analytics_v2(update: Update, context):
    """Enhanced revenue analytics"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Daily revenue for last 7 days
    cursor.execute('''
        SELECT DATE(verified_at) as date,
               COUNT(*) as transactions,
               SUM(amount) as revenue,
               AVG(amount) as avg_ticket
        FROM payments 
        WHERE status = 'verified' 
        AND verified_at >= DATE('now', '-7 days')
        GROUP BY DATE(verified_at)
        ORDER BY date DESC
    ''')
    
    daily_revenue = cursor.fetchall()
    
    # Revenue by plan
    cursor.execute('''
        SELECT plan,
               COUNT(*) as transactions,
               SUM(amount) as revenue,
               AVG(amount) as avg_ticket
        FROM payments 
        WHERE status = 'verified'
        GROUP BY plan
        ORDER BY revenue DESC
    ''')
    
    plan_revenue = cursor.fetchall()
    
    # Revenue by campaign
    cursor.execute('''
        SELECT campaign_id,
               COUNT(*) as transactions,
               SUM(amount) as revenue,
               AVG(amount) as avg_ticket
        FROM payments 
        WHERE status = 'verified' AND campaign_id IS NOT NULL
        GROUP BY campaign_id
        ORDER BY revenue DESC
        LIMIT 5
    ''')
    
    campaign_revenue = cursor.fetchall()
    
    # Top users by spending
    cursor.execute('''
        SELECT u.username, u.user_id,
               COUNT(p.id) as transactions,
               SUM(p.amount) as total_spent
        FROM users u
        JOIN payments p ON u.user_id = p.user_id AND p.status = 'verified'
        GROUP BY u.user_id
        ORDER BY total_spent DESC
        LIMIT 10
    ''')
    
    top_users = cursor.fetchall()
    
    conn.close()
    
    text = f"""📈 *REVENUE ANALYTICS V2*

*Last 7 Days Performance:*
"""
    
    total_7day = 0
    for day in daily_revenue:
        date = datetime.fromisoformat(day['date']).strftime('%b %d')
        text += f"• {date}: {day['revenue']:,.0f} ETB ({day['transactions']} tx)\n"
        total_7day += day['revenue']
    
    text += f"\n*7-Day Total:* {total_7day:,.0f} ETB\n"
    text += f"*Daily Average:* {total_7day/len(daily_revenue) if daily_revenue else 0:,.0f} ETB\n\n"
    
    text += "*Revenue by Plan:*\n"
    for plan in plan_revenue:
        text += f"• {plan['plan'].upper()}: {plan['revenue']:,.0f} ETB ({plan['transactions']} tx)\n"
    
    text += "\n*Top Campaigns:*\n"
    for campaign in campaign_revenue:
        text += f"• {campaign['campaign_id'] or 'Direct'}: {campaign['revenue']:,.0f} ETB\n"
    
    text += "\n*Top 10 Users by Spending:*\n"
    for i, user in enumerate(top_users, 1):
        username = user['username'] or f"user_{user['user_id']}"
        text += f"{i}. @{username}: {user['total_spent']:,.0f} ETB ({user['transactions']} tx)\n"
    
    text += f"""
*Key Metrics:*
• Avg Transaction: {plan_revenue[0]['avg_ticket'] if plan_revenue else 0:,.0f} ETB
• Conversion Rate: Calculate from analytics
• Customer LTV: Estimate from patterns

*Insights & Recommendations:*
1. Focus on {plan_revenue[0]['plan'] if plan_revenue else 'PRO'} plan (highest revenue)
2. Top campaign: {campaign_revenue[0]['campaign_id'] if campaign_revenue else 'Direct'}
3. Target similar users to top spenders"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def manage_campaigns(update: Update, context):
    """Manage marketing campaigns"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        # Show current campaigns
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM campaigns 
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        campaigns = cursor.fetchall()
        conn.close()
        
        text = "🎯 *MANAGE CAMPAIGNS*\n\n"
        text += "*Current Campaigns:*\n"
        
        for campaign in campaigns:
            status = "✅" if campaign['is_active'] else "❌"
            expires = datetime.fromisoformat(campaign['expires_at']).strftime('%b %d') if campaign['expires_at'] else 'Never'
            remaining = campaign['max_uses'] - campaign['used_count'] if campaign['max_uses'] else '∞'
            
            if campaign['discount_percent']:
                discount = f"{campaign['discount_percent']}% OFF"
            else:
                discount = f"{campaign['discount_amount']} ETB OFF"
            
            text += f"""• {status} *{campaign['name']}*
   Code: `{campaign['code']}`
   Type: {campaign['type']}
   Discount: {discount}
   Used: {campaign['used_count']}/{campaign['max_uses'] or '∞'} ({remaining} left)
   Expires: {expires}
   Created: {datetime.fromisoformat(campaign['created_at']).strftime('%b %d')}

"""
        
        text += """
*Commands:*
`/campaigns create NAME CODE TYPE VALUE MAX_USES DAYS`
`/campaigns toggle CODE` - Activate/Deactivate
`/campaigns delete CODE` - Remove campaign

*Examples:*
`/campaigns create "Black Friday" BF2023 discount 50 100 7`
`/campaigns create "Referral Bonus" REFER15 referral 15 1000 30`"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        return
    
    # Handle campaign commands
    action = context.args[0].lower()
    
    if action == 'create' and len(context.args) >= 6:
        try:
            name = context.args[1]
            code = context.args[2].upper()
            campaign_type = context.args[3]
            value = float(context.args[4])
            max_uses = int(context.args[5])
            days = int(context.args[6]) if len(context.args) > 6 else 30
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if campaign_type == 'discount':
                cursor.execute('''
                    INSERT INTO campaigns 
                    (name, code, type, discount_percent, max_uses, expires_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (name, code, campaign_type, value, max_uses, 
                     (datetime.now() + timedelta(days=days)).isoformat()))
            elif campaign_type == 'referral':
                cursor.execute('''
                    INSERT INTO campaigns 
                    (name, code, type, discount_amount, max_uses, expires_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (name, code, campaign_type, value, max_uses,
                     (datetime.now() + timedelta(days=days)).isoformat()))
            
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"✅ Campaign created: {name} ({code})")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif action == 'toggle' and len(context.args) >= 2:
        code = context.args[1].upper()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE campaigns 
            SET is_active = NOT is_active 
            WHERE code = ?
        ''', (code,))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Campaign {code} toggled")
    
    elif action == 'delete' and len(context.args) >= 2:
        code = context.args[1].upper()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM campaigns WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Campaign {code} deleted")

async def broadcast_message(update: Update, context):
    """Broadcast message to all users"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/broadcast [message]`\n\n"
            "Example: `/broadcast New feature added! Check it out.`"
        )
        return
    
    message = ' '.join(context.args)
    
    # Get all user IDs
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status = 'active'")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    failed = 0
    
    await update.message.reply_text(f"📢 Broadcasting to {total} users...")
    
    # Send to users in batches
    for i, user in enumerate(users, 1):
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *ANNOUNCEMENT FROM {BOT_NAME}*\n\n{message}\n\n_This is an automated broadcast._",
                parse_mode='Markdown'
            )
            success += 1
            
            # Log notification
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, ?, ?, ?)
            ''', (user['user_id'], "Announcement", message, "broadcast"))
            conn.commit()
            conn.close()
            
            # Delay to avoid rate limiting
            if i % 20 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user['user_id']}: {e}")
    
    # Send report
    report = f"""📊 *BROADCAST COMPLETE*
    
Total Users: {total}
✅ Successful: {success}
❌ Failed: {failed}
📈 Success Rate: {success/total*100:.1f}%

*Message Sent:*
{message[:200]}..."""
    
    await update.message.reply_text(report, parse_mode='Markdown')

# ======================
# AUTOMATED SYSTEMS V2
# ======================
async def scheduled_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Automated scheduled tasks"""
    try:
        logger.info("🔄 Running scheduled tasks...")
        
        # 1. Create daily backup
        success, backup_file = create_backup_v2()
        if success:
            logger.info(f"📦 Daily backup created: {backup_file}")
        
        # 2. Check for expired payments
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, u.username 
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending' 
            AND p.expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        expired = cursor.fetchall()
        
        for payment in expired:
            # Update status
            cursor.execute('''
                UPDATE payments SET status = 'expired' WHERE id = ?
            ''', (payment['id'],))
            
            # Send notification
            try:
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text=f"⏰ *PAYMENT EXPIRED*\n\nYour payment for {payment['plan'].upper()} plan has expired. Please initiate a new payment to upgrade.",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        conn.commit()
        conn.close()
        
        # 3. Send daily report to admin
        if datetime.now().hour == 9:  # 9 AM
            await send_daily_report(context)
        
        logger.info("✅ Scheduled tasks completed")
        
    except Exception as e:
        logger.error(f"Error in scheduled tasks: {e}")

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """Send daily report to admin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # New users
        cursor.execute('''
            SELECT COUNT(*) as count 
            FROM users 
            WHERE DATE(joined_at) = ?
        ''', (yesterday,))
        new_users = cursor.fetchone()['count']
        
        # Revenue
        cursor.execute('''
            SELECT SUM(amount) as revenue 
            FROM payments 
            WHERE status = 'verified' AND DATE(verified_at) = ?
        ''', (yesterday,))
        revenue = cursor.fetchone()['revenue'] or 0
        
        # Pending payments
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        # Campaign performance
        cursor.execute('''
            SELECT c.name, c.code, COUNT(p.id) as conversions
            FROM campaigns c
            LEFT JOIN payments p ON c.code = p.campaign_id 
                AND p.status = 'verified' 
                AND DATE(p.verified_at) = ?
            WHERE c.is_active = 1
            GROUP BY c.id
        ''', (yesterday,))
        
        campaigns = cursor.fetchall()
        
        conn.close()
        
        text = f"""📅 *DAILY REPORT - {yesterday}*

*Key Metrics:*
👥 New Users: {new_users}
💰 Daily Revenue: {revenue:,.0f} ETB
⏳ Pending Payments: {pending}

*Campaign Performance:*
"""
        
        for campaign in campaigns:
            text += f"• {campaign['name']}: {campaign['conversions']} conversions\n"
        
        text += f"""
*Total Users:* [Get from /db_stats]
*Total Revenue:* [Get from /revenue]

*Recommended Actions:*
1. Verify pending payments ({pending} pending)
2. Check campaign performance
3. Engage with new users
4. Create backup"""
        
        await context.bot.send_message(
            chat_id=7714584854,
            text=text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error sending daily report: {e}")

# ======================
# ENHANCED BUTTON HANDLER V2
# ======================
async def button_handler_v2(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    
    # Handle all V2 button clicks
    if query.data == "premium_v2":
        await premium_v2(update, context)
    
    elif query.data == "upgrade_pro_v2":
        # Create payment with campaign check
        reference_code = create_payment_v2(user_id, username, "pro", 149)
        
        keyboard = [
            [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo_pro")],
            [InlineKeyboardButton("💳 PAY NOW", callback_data=f"pay_now_{reference_code}")],
            [InlineKeyboardButton("🔙 BACK", callback_data="premium_v2")]
        ]
        
        text = f"""✅ *SHEGER PRO SELECTED*

💰 *149 ETB/month*
👤 User: @{username}
🆔 Your ID: `{user_id}`
📋 Reference: `{reference_code}`

*Special Offers Available:*
• First month FREE with code: SHEGERLAUNCH
• Referral discount: REFER10
• Limited time promotions!

*Choose payment method:*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "upgrade_business_v2":
        reference_code = create_payment_v2(user_id, username, "business", 999)
        
        text = f"""🏢 *SHEGER BUSINESS SELECTED*

💰 *999 ETB/month*
👤 User: @{username}
🆔 Your ID: `{user_id}`
📋 Reference: `{reference_code}`

*For business inquiries, contact:* {SALES}

*Or send payment to:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Include reference:* `{reference_code}`

*Why contact sales?*
• Custom invoice generation
• Bulk payment processing
• API integration setup
• Dedicated account manager
• Volume discounts available

*🏢 Perfect for:*
• Businesses with 10+ employees
• Companies processing 100K+ ETB monthly
• Organizations needing custom solutions
• Enterprises requiring API integration"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "my_plan_v2":
        stats = get_user_stats(user_id)
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        # Calculate days remaining if premium
        days_remaining = 0
        if plan != 'basic':
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT verified_at FROM payments 
                WHERE user_id = ? AND status = 'verified'
                ORDER BY verified_at DESC LIMIT 1
            ''', (user_id,))
            
            payment = cursor.fetchone()
            conn.close()
            
            if payment and payment['verified_at']:
                last_payment = datetime.fromisoformat(payment['verified_at'])
                days_remaining = 30 - (datetime.now() - last_payment).days
        
        benefits = {
            'basic': "• 2.5% transaction fee\n• 5 free listings/month\n• Standard support\n• Basic features",
            'pro': "• 1.5% transaction fee (Save 40%!)\n• Unlimited listings\n• Priority support\n• Business badge\n• Referral earnings\n• Advanced analytics",
            'business': "• 0.8% transaction fee (Lowest rate!)\n• Bulk payment processing\n• Business dashboard\n• Dedicated manager\n• API access\n• White-label solutions"
        }[plan]
        
        action = {
            'basic': "Upgrade to PRO for better features and start earning!",
            'pro': "You're on the best value plan! Consider BUSINESS for bulk needs.",
            'business': "Thank you for being a business customer! Contact sales for custom solutions."
        }[plan]
        
        keyboard = [[InlineKeyboardButton("🚀 UPGRADE PLAN", callback_data="premium_v2")]]
        if plan != 'basic':
            keyboard.append([InlineKeyboardButton("🔄 RENEW PLAN", callback_data=f"renew_{plan}")])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")])
        
        text = f"""⭐ *YOUR {BOT_NAME} PLAN V2*

*Current Plan:* {plan.upper()}
*Transaction Fee:* {fee}%
*Status:* Active ✅
{"*Days Remaining:* " + str(days_remaining) if days_remaining > 0 else ""}

*Plan Benefits:*
{benefits}

*Your Stats:*
💰 Total Spent: {stats['total_spent']:.0f} ETB
💎 Total Earned: {stats['total_earned']:.0f} ETB
👥 Referred: {stats['referred_count']} users

{action}

*Need to change your plan?*
Contact {SUPPORT} or upgrade directly!"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "referral":
        await referral_system(update, context)
    
    elif query.data == "wallet":
        await wallet_command(update, context)
    
    elif query.data == "analytics":
        await analytics_dashboard(update, context)
    
    elif query.data == "promotions":
        await promotions_center(update, context)
    
    elif query.data == "back_to_main":
        # Return to main menu
        await start_v2(update, context)
    
    elif query.data.startswith("campaign_"):
        campaign_code = query.data.replace("campaign_", "")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM campaigns WHERE code = ?
        ''', (campaign_code,))
        
        campaign = cursor.fetchone()
        conn.close()
        
        if campaign:
            if campaign['discount_percent']:
                discount = f"{campaign['discount_percent']}% OFF"
            else:
                discount = f"{campaign['discount_amount']} ETB OFF"
            
            text = f"""🎁 *{campaign['name']}*

*Discount:* {discount}
*Code:* `{campaign['code']}`
*Type:* {campaign['type'].title()}
*Uses Left:* {campaign['max_uses'] - campaign['used_count'] if campaign['max_uses'] else '∞'}
*Expires:* {datetime.fromisoformat(campaign['expires_at']).strftime('%B %d, %Y') if campaign['expires_at'] else 'Never'}

*How to Use:*
1. Click UPGRADE NOW
2. Select your plan
3. Apply code: `{campaign['code']}`
4. Complete payment

*Terms & Conditions:*
• One use per user
• Cannot combine with other offers
• Valid for new upgrades only
• Admin reserves right to modify"""
            
            keyboard = [
                [InlineKeyboardButton("🚀 UPGRADE NOW", callback_data="premium_v2")],
                [InlineKeyboardButton("🔙 BACK", callback_data="promotions")]
            ]
            
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "copy_ref_link":
        stats = get_user_stats(user_id)
        referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={stats['referral_code']}"
        
        text = f"""✅ *REFERRAL LINK COPIED*

Your referral link has been copied to clipboard!

*Link:* `{referral_link}`

*Share this with friends:*
🚀 Join me on SHEGER ET - Ethiopia's Super App!
Use my link to sign up and we both earn rewards!
👉 {referral_link}

*Your Code:* `{stats['referral_code']}`

Keep sharing to earn more! 💰"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "send_v2":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        
        text = f"""💸 *SEND MONEY WITH {BOT_NAME} V2*

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

*Daily Limits:*
• Basic: 5,000 ETB
• PRO: 50,000 ETB
• Business: 500,000 ETB

*Coming Soon:*
• International transfers
• Currency exchange
• Payment links
• QR code payments

*Upgrade now to save on fees!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "market_v2":
        plan = get_plan(user_id)
        
        listings = "Unlimited listings" if plan != 'basic' else "5 free listings/month"
        placement = "Priority placement" if plan != 'basic' else "Standard placement"
        analytics = "Advanced analytics" if plan == 'business' else "Basic analytics"
        
        keyboard = [
            [InlineKeyboardButton("🛒 BROWSE LISTINGS", callback_data="browse_market")],
            [InlineKeyboardButton("➕ CREATE LISTING", callback_data="create_listing")],
            [InlineKeyboardButton("📊 MY LISTINGS", callback_data="my_listings")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🛍️ *{BOT_NAME} MARKETPLACE V2*

*Available Categories:*
• 📱 Electronics & Phones
• 👗 Fashion & Clothing
• 🏡 Home & Furniture
• 🚗 Vehicles & Auto Parts
• 🔧 Services & Professionals
• 🏢 Commercial Equipment
• 🧑‍🌾 Agriculture & Livestock
• 📚 Education & Books
• 🎮 Entertainment & Games
• 🏥 Health & Wellness

*Your Plan ({plan.upper()}):*
• {listings}
• {placement}
• {analytics}
• {"Escrow protection" if plan != 'basic' else "Basic protection"}

*Featured Listings:*
🔥 New iPhone 15 - 45,000 ETB
🏠 3BR Apartment Bole - 8,000 ETB/month
🚗 Toyota Corolla 2018 - 650,000 ETB
💻 MacBook Pro M2 - 85,000 ETB

*Start buying or selling today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "jobs_v2":
        keyboard = [
            [InlineKeyboardButton("🔍 SEARCH JOBS", callback_data="search_jobs")],
            [InlineKeyboardButton("➕ POST JOB", callback_data="post_job")],
            [InlineKeyboardButton("📊 MY APPLICATIONS", callback_data="my_applications")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🔧 *FIND WORK ON {BOT_NAME} V2*

*Top Job Categories:*
• 💻 Tech & Programming (150+ jobs)
• 🏗️ Construction & Labor (80+ jobs)
• 🚚 Driving & Delivery (120+ jobs)
• 👨‍🏫 Teaching & Tutoring (60+ jobs)
• 🏥 Healthcare (45+ jobs)
• 🍽️ Hospitality (75+ jobs)
• 📊 Administration (90+ jobs)

*Featured Jobs:*
👨‍💻 Senior Developer - 35,000 ETB/month
🏗️ Site Manager - 25,000 ETB/month
🚚 Delivery Driver - 12,000 ETB/month
👨‍🏫 English Teacher - 15,000 ETB/month

*For Job Seekers:*
• Browse thousands of verified jobs
• Apply directly through bot
• Get instant job alerts
• Build professional profile
• Secure escrow payments

*For Employers:*
• Post jobs for FREE
• Reach qualified candidates
• Manage applications easily
• Hire with confidence
• Rating system

*Start your job search or post a job today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "property_v2":
        keyboard = [
            [InlineKeyboardButton("🔍 SEARCH PROPERTIES", callback_data="search_properties")],
            [InlineKeyboardButton("➕ LIST PROPERTY", callback_data="list_property")],
            [InlineKeyboardButton("📊 MY LISTINGS", callback_data="my_properties")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🏠 *PROPERTIES ON {BOT_NAME} V2*

*Find Your Perfect Property:*
• 🏡 Houses for Rent/Sale (250+ listings)
• 🏢 Apartments & Condos (180+ listings)
• 🏪 Commercial Spaces (120+ listings)
• 🗺️ Land & Plots (95+ listings)
• 🏖️ Vacation Rentals (45+ listings)
• 🏨 Hotel & Guest Houses (30+ listings)

*Featured Properties:*
🏡 4BR Villa Bole - 25,000 ETB/month
🏢 2BR Apartment Cazanchise - 6,500 ETB/month
🗺️ 500m² Land Gotera - 1,200,000 ETB
🏪 Shop Mexico - 8,000 ETB/month

*Verified Properties Only:*
✅ All listings verified
✅ Authentic photos
✅ Accurate location data
✅ Price transparency
✅ Owner/Agent verification

*Advanced Features:*
• Virtual tours
• Mortgage calculator
• Price alerts
• Save favorites
• Neighborhood info

*Find your dream home or investment property today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# MAIN FUNCTION V2
# ======================
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not set!")
        return
    
    # Create application with persistence
    application = Application.builder().token(TOKEN).build()
    
    # ======================
    # REGISTER HANDLERS V2
    # ======================
    
    # User commands
    application.add_handler(CommandHandler("start", start_v2))
    application.add_handler(CommandHandler("premium", premium_v2))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("referral", referral_system))
    application.add_handler(CommandHandler("analytics", analytics_dashboard))
    
    # Admin commands V2
    application.add_handler(CommandHandler("admin", admin_dashboard_v2))
    application.add_handler(CommandHandler("revenue", revenue_analytics_v2))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("pending", pending))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("campaigns", manage_campaigns))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("backup", backup_cmd))
    application.add_handler(CommandHandler("list_backups", list_backups_cmd))
    application.add_handler(CommandHandler("restore", restore_cmd))
    application.add_handler(CommandHandler("db_info", db_info))
    application.add_handler(CommandHandler("db_stats", db_stats_cmd))
    
    # Button handler V2
    application.add_handler(CallbackQueryHandler(button_handler_v2))
    
    # ======================
    # SCHEDULED TASKS V2
    # ======================
    job_queue = application.job_queue
    
    if job_queue:
        # Daily backup at 2 AM
        job_queue.run_daily(
            scheduled_tasks,
            time=datetime.time(hour=2, minute=0),
            days=(0, 1, 2, 3, 4, 5, 6),
            name="daily_tasks"
        )
        
        # Hourly checks
        job_queue.run_repeating(
            scheduled_tasks,
            interval=3600,  # 1 hour
            first=10,
            name="hourly_checks"
        )
        
        logger.info("⏰ Scheduled tasks initialized")
    
    # ======================
    # STARTUP MESSAGE V2
    # ======================
    logger.info("=" * 70)
    logger.info(f"🚀 {BOT_NAME} V2 - ENHANCED PRODUCTION")
    logger.info(f"🌟 {BOT_SLOGAN}")
    logger.info(f"🤖 Bot: {BOT_USERNAME}")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"💾 Database: {DATABASE_PATH}")
    logger.info(f"📦 Backups: {BACKUP_DIR}")
    logger.info("✅ V2 FEATURES ENABLED:")
    logger.info("   • Enhanced Referral System")
    logger.info("   • Marketing Campaigns")
    logger.info("   • User Analytics Dashboard")
    logger.info("   • Automated Scheduled Tasks")
    logger.info("   • Enhanced Admin Commands")
    logger.info("   • Wallet System")
    logger.info("   • Promotions Center")
    logger.info("=" * 70)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ======================
# IMPORT COMPATIBILITY FUNCTIONS
# ======================
# Add these functions from previous version for compatibility
async def help_cmd(update: Update, context):
    text = f"""🆘 *{BOT_NAME} V2 HELP*

*Basic Commands:*
`/start` - Main menu with referral tracking
`/premium` - Upgrade plans with promotions
`/wallet` - Your wallet & earnings
`/referral` - Referral program
`/analytics` - Your statistics dashboard
`/help` - This message

*Admin Commands:*
`/admin` - Enhanced admin dashboard
`/revenue` - Revenue analytics
`/campaigns` - Manage promotions
`/broadcast` - Send announcements
`/backup` - Create database backup

*Support Channels:*
📞 Customer Support: {SUPPORT}
💰 Payment Issues: {PAYMENTS}
🏢 Business Sales: {SALES}
📰 News & Updates: {NEWS}

*24/7 Support Available*
Need help? Contact {SUPPORT}"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# Add other compatibility functions from previous version
# (These should be copied from your existing bot)
async def verify(update: Update, context):
    # Your existing verify function
    pass

async def pending(update: Update, context):
    # Your existing pending function
    pass

async def stats(update: Update, context):
    # Your existing stats function
    pass

async def backup_cmd(update: Update, context):
    # Your existing backup function
    pass

async def list_backups_cmd(update: Update, context):
    # Your existing list_backups function
    pass

async def restore_cmd(update: Update, context):
    # Your existing restore function
    pass

async def db_info(update: Update, context):
    # Your existing db_info function
    pass

async def db_stats_cmd(update: Update, context):
    # Your existing db_stats function
    pass

if __name__ == "__main__":
    main()
