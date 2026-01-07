#!/usr/bin/env python3
"""
SHEGER - Ethiopian Super-App Bot
Complete version with revenue tracking and premium features
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ======================
# LOGGING SETUP
# ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# DATA PERSISTENCE SETUP
# ======================
DATA_FILE = "sheger_data.json"

def load_data():
    """Load data from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {
        "users": {},
        "payments": [],
        "pending_payments": {},
        "listings": [],
        "transactions": []
    }

def save_data():
    """Save data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# Load initial data
data = load_data()
users_db = data["users"]
revenue_log = data["payments"]
pending_payments = data["pending_payments"]
listings_db = data["listings"]
transactions_db = data["transactions"]

# ======================
# CONSTANTS
# ======================
TIER_BASIC = "basic"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"

PRICING = {
    TIER_PRO: {"monthly": 149, "yearly": 1499},
    TIER_ENTERPRISE: {"monthly": 999, "yearly": 9999}
}

FEES = {
    TIER_BASIC: 2.5,
    TIER_PRO: 1.5,
    TIER_ENTERPRISE: 0.8
}

# ======================
# HELPER FUNCTIONS
# ======================
def get_user(user_id: int) -> Dict:
    """Get or create user data"""
    user_id_str = str(user_id)
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            "id": user_id,
            "tier": TIER_BASIC,
            "joined": datetime.now().isoformat(),
            "subscription_end": None,
            "balance": 0.0,
            "free_listings_used": 0,
            "free_listings_reset": datetime.now().isoformat(),
            "phone": None,
            "trust_score": 50,
            "total_spent": 0.0
        }
        save_data()
    return users_db[user_id_str]

def update_user(user_id: int, updates: Dict):
    """Update user data and save"""
    user_id_str = str(user_id)
    if user_id_str in users_db:
        users_db[user_id_str].update(updates)
        save_data()

def calculate_fee(amount: float, user_id: int) -> float:
    """Calculate transaction fee"""
    user = get_user(user_id)
    fee_percentage = FEES[user["tier"]]
    return (amount * fee_percentage) / 100

def can_user_list_item(user_id: int) -> bool:
    """Check if user can create new listing"""
    user = get_user(user_id)
    
    # Reset free listings monthly
    reset_date = datetime.fromisoformat(user.get("free_listings_reset", datetime.now().isoformat()))
    if datetime.now() - reset_date > timedelta(days=30):
        update_user(user_id, {"free_listings_used": 0, "free_listings_reset": datetime.now().isoformat()})
        user = get_user(user_id)
    
    if user["tier"] == TIER_BASIC:
        return user["free_listings_used"] < 3
    return True  # Pro and Enterprise have unlimited

def log_payment(user_id: int, amount: float, plan: str, method: str = "manual"):
    """Log a successful payment"""
    payment_record = {
        "user_id": user_id,
        "amount": amount,
        "plan": plan,
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }
    
    revenue_log.append(payment_record)
    
    # Update user total spent
    user = get_user(user_id)
    user["total_spent"] = user.get("total_spent", 0) + amount
    update_user(user_id, {"total_spent": user["total_spent"]})
    
    # Remove from pending
    user_id_str = str(user_id)
    if user_id_str in pending_payments:
        del pending_payments[user_id_str]
    
    save_data()
    logger.info(f"💰 Payment logged: User {user_id} -> {plan} ({amount} ETB)")
    
    return payment_record

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    admin_id = os.getenv("ADMIN_USER_ID", "")
    return str(user_id) == admin_id or user_id == 7714584854  # Your fallback ID

# ======================
# COMMAND HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu command"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    # Check subscription status
    if user_data["tier"] in [TIER_PRO, TIER_ENTERPRISE] and user_data.get("subscription_end"):
        end_date = datetime.fromisoformat(user_data["subscription_end"])
        if datetime.now() > end_date:
            # Subscription expired
            update_user(user.id, {"tier": TIER_BASIC, "subscription_end": None})
            user_data = get_user(user.id)
    
    # Welcome message based on tier
    if user_data["tier"] == TIER_BASIC:
        tier_info = f"*Plan:* BASIC (Upgrade: /premium)"
        listings_left = f"Listings left: {3 - user_data['free_listings_used']}/3"
    else:
        tier_info = f"*Plan:* {user_data['tier'].upper()} 🎉"
        listings_left = "Unlimited listings"
    
    welcome = f"""🌟 *Welcome to SHEGER* 🇪🇹

*Your All-in-One Ethiopian Super-App*

👤 Account: @{user.username}
💰 {tier_info}
💳 Balance: {user_data['balance']:,.2f} ETB
📊 {listings_left}

*Quick Actions:*
💸 `/send` - Send money (Fee: {FEES[user_data['tier']]}%)
🛍️ `/market` - Buy & sell goods
🔧 `/gigs` - Find work opportunities
🏠 `/property` - Property listings
📚 `/learn` - Skills & courses
⚙️ `/profile` - Your account

⭐ `/premium` - Upgrade plan
🆘 `/help` - Support center"""
    
    keyboard = [
        [
            InlineKeyboardButton("💸 Send Money", callback_data="send_money"),
            InlineKeyboardButton("🛍️ Marketplace", callback_data="marketplace")
        ],
        [
            InlineKeyboardButton("🔧 Find Work", callback_data="gigs"),
            InlineKeyboardButton("📚 Learn", callback_data="learn")
        ],
        [
            InlineKeyboardButton("⚙️ Profile", callback_data="profile"),
            InlineKeyboardButton("⭐ Upgrade", callback_data="premium_menu")
        ]
    ]
    
    await update.message.reply_text(
        welcome,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium plans menu"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    message = f"""🚀 *SHEGER Premium Plans*

*Your Current Plan:* {user_data['tier'].upper()}

*1. SHEGER PRO* - 149 ETB/month
• Transaction fee: *1.5%* (vs 2.5% Basic)
• Unlimited marketplace listings
• Priority access to gig jobs
• Business profile with verification badge
• Daily limit: *50,000 ETB*
• 24-hour support response

*2. SHEGER ENTERPRISE* - 999 ETB/month
• Transaction fee: *0.8%* (Lowest rate!)
• Bulk payment processing
• Custom business portal
• Advanced API access
• Dedicated account manager
• White-label solutions
• *Unlimited* transaction limits

*🎁 SPECIAL LAUNCH OFFER:*
First month *FREE* on any plan!
Use code: `SHEGERLAUNCH`

Choose your plan below:"""
    
    keyboard = [
        [
            InlineKeyboardButton("🟢 PRO Monthly - 149 ETB", callback_data="upgrade_pro_monthly"),
            InlineKeyboardButton("🟢 PRO Yearly - 1,499 ETB", callback_data="upgrade_pro_yearly")
        ],
        [
            InlineKeyboardButton("🔵 ENTERPRISE Monthly - 999 ETB", callback_data="upgrade_enterprise_monthly"),
            InlineKeyboardButton("🔵 ENTERPRISE Yearly - 9,999 ETB", callback_data="upgrade_enterprise_yearly")
        ],
        [
            InlineKeyboardButton("📞 Contact Sales", callback_data="contact_sales"),
            InlineKeyboardButton("❓ FAQ", callback_data="premium_faq")
        ]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send money command"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not context.args or len(context.args) < 2:
        usage = f"""💸 *Send Money*

Usage: `/send [amount] [phone_number]`
Example: `/send 500 0912345678`

*Your current fee:* {FEES[user_data['tier']]}%
*Daily limit:* {"5,000" if user_data['tier'] == TIER_BASIC else "50,000" if user_data['tier'] == TIER_PRO else "Unlimited"} ETB

*Supported payment methods:*
• telebirr
• M-Pesa Ethiopia
• CBE Birr
• Dashen Bank
• Cash pickup"""
        
        await update.message.reply_text(usage, parse_mode='Markdown')
        return
    
    try:
        amount = float(context.args[0])
        phone = context.args[1]
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0.")
            return
        
        # Check limits
        if user_data["tier"] == TIER_BASIC and amount > 5000:
            await update.message.reply_text(
                "❌ *Limit Exceeded*\n\n"
                "Basic users can send maximum 5,000 ETB per day.\n"
                "Upgrade to PRO for 50,000 ETB daily limit:\n"
                "`/premium`",
                parse_mode='Markdown'
            )
            return
        
        # Calculate fee
        fee = calculate_fee(amount, user.id)
        total = amount + fee
        
        message = f"""✅ *Payment Ready*

📱 To: `{phone}`
💰 Amount: *{amount:,.2f} ETB*
💸 Fee ({FEES[user_data['tier']]}%): *{fee:,.2f} ETB*
💳 Total: *{total:,.2f} ETB*

*Choose payment method:*"""
        
        keyboard = [
            [
                InlineKeyboardButton("📱 telebirr", callback_data=f"pay_telebirr_{amount}_{phone}"),
                InlineKeyboardButton("🟢 M-Pesa", callback_data=f"pay_mpesa_{amount}_{phone}")
            ],
            [
                InlineKeyboardButton("🏦 CBE Birr", callback_data=f"pay_cbe_{amount}_{phone}"),
                InlineKeyboardButton("💵 Cash", callback_data=f"pay_cash_{amount}_{phone}")
            ]
        ]
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
    except Exception as e:
        logger.error(f"Error in send_money: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marketplace command"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not context.args:
        # Show marketplace menu
        listings_left = f"{3 - user_data['free_listings_used']}/3" if user_data['tier'] == TIER_BASIC else "Unlimited"
        
        message = f"""🛍️ *SHEGER Marketplace*

📊 Your listings: *{listings_left}* left
⭐ Upgrade for unlimited: `/premium`

*Categories:*
• 📱 Electronics & Phones
• 👕 Fashion & Clothing
• 🏡 Home & Furniture
• 🚗 Vehicles & Parts
• 🔧 Services
• 🏠 Property & Real Estate
• 🛒 General Goods

*Commands:*
`/market buy [item]` - Search items
`/market sell [item] [price] [location?]` - List item
`/market mine` - Your listings
`/market featured` - Premium listings"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Browse", callback_data="browse_market"),
                InlineKeyboardButton("📤 Sell Item", callback_data="sell_item_form")
            ],
            [
                InlineKeyboardButton("⭐ Featured", callback_data="featured_items"),
                InlineKeyboardButton("📈 My Listings", callback_data="my_listings")
            ]
        ]
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Handle subcommands
    subcommand = context.args[0].lower()
    
    if subcommand == "sell":
        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage: `/market sell [item name] [price] [location?]`\n"
                "Example: `/market sell iPhone 12 15000 Addis Ababa`"
            )
            return
        
        # Check if user can list
        if not can_user_list_item(user.id):
            await update.message.reply_text(
                "❌ *Monthly Limit Reached*\n\n"
                "Basic users get 3 free listings per month.\n"
                "Upgrade to PRO for unlimited listings:\n"
                "`/premium`",
                parse_mode='Markdown'
            )
            return
        
        item_name = " ".join(context.args[1:-2])
        price = context.args[-2]
        location = context.args[-1] if len(context.args) > 3 else "Addis Ababa"
        
        # Create listing
        listing = {
            "id": len(listings_db) + 1,
            "user_id": user.id,
            "username": user.username,
            "item": item_name,
            "price": price,
            "location": location,
            "category": "general",
            "premium": user_data["tier"] != TIER_BASIC,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        listings_db.append(listing)
        
        # Update user's listing count
        if user_data["tier"] == TIER_BASIC:
            update_user(user.id, {"free_listings_used": user_data["free_listings_used"] + 1})
        
        save_data()
        
        premium_badge = "⭐ " if listing["premium"] else ""
        
        await update.message.reply_text(
            f"✅ *Item Listed Successfully!*\n\n"
            f"{premium_badge}*Item:* {item_name}\n"
            f"💰 *Price:* {price} ETB\n"
            f"📍 *Location:* {location}\n"
            f"👤 *Seller:* @{user.username}\n\n"
            f"*Listing Code:* `MKT{listing['id']:04d}`\n"
            f"*Listings used:* {get_user(user.id)['free_listings_used']}/3",
            parse_mode='Markdown'
        )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User profile command"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    # Calculate stats
    user_listings = [l for l in listings_db if l.get("user_id") == user.id]
    user_payments = [p for p in revenue_log if p.get("user_id") == user.id]
    
    # Subscription info
    if user_data["subscription_end"]:
        end_date = datetime.fromisoformat(user_data["subscription_end"])
        days_left = (end_date - datetime.now()).days
        sub_info = f"Expires in: {days_left} days"
    else:
        sub_info = "No active subscription"
    
    message = f"""⚙️ *Your SHEGER Profile*

*Account Info:*
👤 Username: @{user.username}
🆔 User ID: `{user.id}`
📅 Joined: {datetime.fromisoformat(user_data['joined']).strftime('%b %d, %Y')}
⭐ Trust Score: {user_data['trust_score']}/100

*Subscription:*
🎫 Plan: *{user_data['tier'].upper()}*
💰 Total Spent: {user_data.get('total_spent', 0):,.2f} ETB
📅 {sub_info}

*Stats:*
🛍️ Listings: {len(user_listings)} active
💸 Payments: {len(user_payments)} completed
💳 Balance: {user_data['balance']:,.2f} ETB

*Actions:*
`/premium` - Upgrade your plan
`/market mine` - Your listings
`/balance` - Add funds
`/verify` - Verify account
`/help` - Get support"""
    
    keyboard = [
        [InlineKeyboardButton("⭐ Upgrade Plan", callback_data="premium_menu")],
        [InlineKeyboardButton("📊 View Stats", callback_data="detailed_stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """🆘 *SHEGER Help Center*

*Quick Commands:*
`/start` - Main menu
`/send [amount] [phone]` - Send money
`/market` - Buy & sell goods
`/gigs` - Find work opportunities
`/premium` - Upgrade account
`/profile` - Your profile
`/balance` - Check balance
`/help` - This message

*Support Channels:*
📞 Customer Support: @ShegerSupport
🐛 Report Bug: @ShegerBugs
💡 Suggestions: @ShegerIdeas
📰 News & Updates: @ShegerNews

*Business Hours:*
Monday - Friday: 8:00 AM - 6:00 PM EAT
Saturday: 9:00 AM - 1:00 PM EAT
Sunday: Closed

*Emergency Contact:*
+251 963 163 418 (Telegram preferred)

*Payment Issues?*
Forward payment receipt to @ShegerPayments"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ======================
# REVENUE & ADMIN COMMANDS
# ======================
async def revenue_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /revenue - View revenue stats"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not revenue_log:
        await update.message.reply_text("📊 *Revenue Report*\n\nNo revenue yet.")
        return
    
    # Calculate stats
    total_revenue = sum(p["amount"] for p in revenue_log)
    total_subscribers = len(revenue_log)
    
    # Group by plan
    pro_payments = [p for p in revenue_log if p["plan"] == TIER_PRO]
    enterprise_payments = [p for p in revenue_log if p["plan"] == TIER_ENTERPRISE]
    
    pro_count = len(pro_payments)
    enterprise_count = len(enterprise_payments)
    pro_revenue = sum(p["amount"] for p in pro_payments)
    enterprise_revenue = sum(p["amount"] for p in enterprise_payments)
    
    # Last 30 days revenue
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_payments = [
        p for p in revenue_log 
        if datetime.fromisoformat(p["timestamp"]) > thirty_days_ago
    ]
    monthly_revenue = sum(p["amount"] for p in recent_payments)
    
    report = f"""💰 *SHEGER Revenue Report*

*Overall Stats:*
Total Revenue: *{total_revenue:,.2f} ETB*
Total Subscribers: *{total_subscribers}*
Monthly (30 days): *{monthly_revenue:,.2f} ETB*

*By Plan:*
• PRO: {pro_count} subscribers ({pro_revenue:,.2f} ETB)
• ENTERPRISE: {enterprise_count} subscribers ({enterprise_revenue:,.2f} ETB)

*Pending Payments:* {len(pending_payments)}

*Recent Payments (Last 5):*
"""
    
    # Show last 5 payments
    for i, payment in enumerate(revenue_log[-5:][::-1], 1):
        timestamp = datetime.fromisoformat(payment["timestamp"]).strftime("%b %d, %H:%M")
        report += f"{i}. User {payment['user_id']} - {payment['plan'].upper()} - {payment['amount']:,.2f} ETB - {timestamp}\n"
    
    keyboard = [[InlineKeyboardButton("📋 Pending List", callback_data="admin_pending")]]
    
    await update.message.reply_text(
        report,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /verify [user_id] [plan] [amount] - Verify payment"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/verify [user_id] [plan] [amount]`\n"
            "Example: `/verify 123456789 pro 149`\n"
            "Example: `/verify 123456789 enterprise 999`"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        plan = context.args[1] if len(context.args) > 1 else TIER_PRO
        amount = float(context.args[2]) if len(context.args) > 2 else PRICING[plan]["monthly"]
        
        if plan not in [TIER_PRO, TIER_ENTERPRISE]:
            await update.message.reply_text("❌ Invalid plan. Use 'pro' or 'enterprise'.")
            return
        
        # Log the payment
        payment = log_payment(target_user_id, amount, plan)
        
        # Update user tier
        subscription_end = datetime.now() + timedelta(days=30)
        update_user(target_user_id, {
            "tier": plan,
            "subscription_end": subscription_end.isoformat(),
            "free_listings_used": 0  # Reset for premium users
        })
        
        # Try to notify user
        try:
            bot = context.bot
            await bot.send_message(
                chat_id=target_user_id,
                text=f"""🎉 *Your SHEGER {plan.upper()} Plan is ACTIVE!*

• Transaction fee: {FEES[plan]}%
• Unlimited marketplace listings
• Priority access to features
• Premium support

Your plan is active until: {subscription_end.strftime('%B %d, %Y')}

Thank you for upgrading! 🚀
Use `/start` to explore premium features."""
            )
            user_notified = True
        except:
            user_notified = False
        
        await update.message.reply_text(
            f"✅ *Payment Verified Successfully!*\n\n"
            f"👤 User: {target_user_id}\n"
            f"🎫 Plan: {plan.upper()}\n"
            f"💰 Amount: {amount:,.2f} ETB\n"
            f"📅 Active until: {subscription_end.strftime('%b %d, %Y')}\n"
            f"📲 User notified: {'✅' if user_notified else '❌'}\n\n"
            f"*Total revenue now:* {sum(p['amount'] for p in revenue_log):,.2f} ETB",
            parse_mode='Markdown'
        )
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Error: {e}\nMake sure user_id is a number.")
    except Exception as e:
        logger.error(f"Error in verify_payment: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def list_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /payments - List pending payments"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return
    
    if not pending_payments:
        await update.message.reply_text("📭 No pending payments.")
        return
    
    report = "⏳ *Pending Payments*\n\n"
    total_pending = 0
    
    for user_id_str, details in pending_payments.items():
        user_info = users_db.get(user_id_str, {})
        username = f"@{user_info.get('username', 'N/A')}" if user_info.get('username') else "No username"
        report += f"• User {user_id_str} ({username}): {details['plan'].upper()} - {details['amount']} ETB\n"
        total_pending += details['amount']
    
    report += f"\n*Total pending:* {len(pending_payments)} users, {total_pending:,.2f} ETB"
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh_pending")]]
    
    await update.message.reply_text(
        report,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /stats - Detailed statistics"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return
    
    # User statistics
    total_users = len(users_db)
    basic_users = sum(1 for u in users_db.values() if u["tier"] == TIER_BASIC)
    pro_users = sum(1 for u in users_db.values() if u["tier"] == TIER_PRO)
    enterprise_users = sum(1 for u in users_db.values() if u["tier"] == TIER_ENTERPRISE)
    
    # Active users (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_users = sum(
        1 for u in users_db.values() 
        if datetime.fromisoformat(u.get("joined", datetime.now().isoformat())) > seven_days_ago
    )
    
    # Platform stats
    total_listings = len(listings_db)
    active_listings = sum(1 for l in listings_db if l.get("status") == "active")
    premium_listings = sum(1 for l in listings_db if l.get("premium") == True)
    
    stats = f"""📊 *SHEGER Platform Statistics*

*User Statistics:*
Total Users: *{total_users}*
Active (7 days): *{active_users}*
• BASIC: {basic_users} users
• PRO: {pro_users} users
• ENTERPRISE: {enterprise_users} users

*Platform Activity:*
Listings: {total_listings} total, {active_listings} active
Premium Listings: {premium_listings}
Transactions: {len(transactions_db)}

*Financial:*
Total Revenue: *{sum(p['amount'] for p in revenue_log):,.2f} ETB*
Pending Payments: {len(pending_payments)}
Avg. Revenue/User: {sum(p['amount'] for p in revenue_log)/max(total_users, 1):,.2f} ETB

*Data:*
Users stored: {len(users_db)}
Payments logged: {len(revenue_log)}"""
    
    await update.message.reply_text(stats, parse_mode='Markdown')

# ======================
# BUTTON HANDLER
# ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "send_money":
        await query.edit_message_text(
            "💸 *Send Money*\n\nUsage: `/send [amount] [phone_number]`\nExample: `/send 500 09613930011`",
            parse_mode='Markdown'
        )
    
    elif data == "premium_menu":
        await premium(update, context)
    
    elif data.startswith("upgrade_"):
        # Handle upgrade selections
        parts = data.split("_")
        plan = parts[1]  # pro or enterprise
        period = parts[2] if len(parts) > 2 else "monthly"
        
        amount = PRICING[plan][period]
        pending_payments[str(user_id)] = {"plan": plan, "amount": amount, "period": period}
        save_data()
        
        if plan == TIER_PRO:
            message = f"""✅ *PRO Plan Selected*

💰 Price: {amount:,} ETB/{period}
🆔 Your User ID: `{user_id}`

*Payment Instructions:*
1. Send *{amount:,} ETB* to:
   • telebirr: *0961 393 001*
   • CBE: *1000 6458 65603*

2. Forward payment receipt to @ShegerPayments
   Include this code: *PRO-{user_id}*

3. We'll activate within 1 hour!

*🎁 LAUNCH OFFER:*
First month FREE with code: `SHEGERLAUNCH`"""
        
        else:  # ENTERPRISE
            message = f"""✅ *ENTERPRISE Plan Selected*

💰 Price: {amount:,} ETB/{period}
🆔 Your User ID: `{user_id}`

*Contact @ShegerSales for professional invoice*
or send payment to:
• telebirr: 0961 393 001
• CBE: 1000 6458 65603

Include reference: *ENT-{user_id}*

*Enterprise Features:*
• Dedicated account manager
• Custom business portal
• Bulk payment processing
• Advanced analytics
• White-label solutions"""
        
        keyboard = [[InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]]
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_pending":
        await list_payments(update, context)
    
    elif data == "profile":
        await profile(update, context)
    
    elif data == "marketplace":
        await market(update, context)
    
    else:
        await query.edit_message_text("⚙️ Feature coming soon! Use /help for available commands.")

# ======================
# MAIN FUNCTION
# ======================
def main():
    """Start the bot."""
    # Get bot token
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("ERROR: TELEGRAM_TOKEN environment variable not set!")
        logger.error("Add it in Railway Dashboard → Variables")
        return
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("send", send_money))
    app.add_handler(CommandHandler("market", market))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_command))
    
    # Admin commands
    app.add_handler(CommandHandler("revenue", revenue_report))
    app.add_handler(CommandHandler("verify", verify_payment))
    app.add_handler(CommandHandler("payments", list_payments))
    app.add_handler(CommandHandler("stats", admin_stats))
    
    # Button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the bot
    logger.info("🚀 SHEGER Bot Starting...")
    logger.info(f"📊 Loaded: {len(users_db)} users, {len(revenue_log)} payments")
    
    # Check admin setup
    admin_id = os.getenv("ADMIN_USER_ID")
    if admin_id:
        logger.info(f"👑 Admin User ID: {admin_id}")
    else:
        logger.warning("⚠️  ADMIN_USER_ID not set. Admin commands won't work.")
    
    app.run_polling()

if __name__ == "__main__":
    main()
