#!/usr/bin/env python3
"""
SHEGER - Ethiopian Super-App Bot
Transforming from Ethio-Pay-Bot to full-scale platform
"""

import os
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

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# DATABASE SIMULATION (Start with simple dict, upgrade later)
# ======================
users_db = {}  # user_id -> user_data
transactions_db = []
listings_db = []

# User tiers
TIER_BASIC = "basic"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"

# Pricing in ETB
PRICING = {
    TIER_BASIC: {"monthly": 0, "yearly": 0},
    TIER_PRO: {"monthly": 149, "yearly": 1499},
    TIER_ENTERPRISE: {"monthly": 999, "yearly": 9999}
}

# Transaction fees (in percentage)
FEES = {
    TIER_BASIC: 2.5,
    TIER_PRO: 1.5,
    TIER_ENTERPRISE: 0.8
}

# ======================
# HELPER FUNCTIONS
# ======================
def get_user_tier(user_id: int) -> str:
    """Get user's subscription tier"""
    if user_id not in users_db:
        # New user - default to basic
        users_db[user_id] = {
            "tier": TIER_BASIC,
            "joined": datetime.now(),
            "subscription_end": None,
            "balance": 0.0,
            "trust_score": 50,
            "free_listings_used": 0,
            "phone": None
        }
    return users_db[user_id]["tier"]

def can_user_list_item(user_id: int) -> bool:
    """Check if user can create new listing based on tier"""
    tier = get_user_tier(user_id)
    
    if tier == TIER_BASIC:
        # Basic users get 3 free listings per month
        user_data = users_db[user_id]
        if user_data["free_listings_used"] < 3:
            return True
        return False
    # Pro and Enterprise have unlimited
    return True

def calculate_fee(amount: float, user_id: int) -> float:
    """Calculate transaction fee based on user tier"""
    tier = get_user_tier(user_id)
    fee_percentage = FEES[tier]
    return (amount * fee_percentage) / 100

def is_premium_user(user_id: int) -> bool:
    """Check if user has paid subscription"""
    tier = get_user_tier(user_id)
    return tier in [TIER_PRO, TIER_ENTERPRISE]

# ======================
# COMMAND HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with main menu"""
    user = update.effective_user
    
    # Check if this is a migrated user from Ethio-Pay-Bot
    welcome_msg = f"""🌟 *Welcome to SHEGER* 🇪🇹

*Your All-in-One Ethiopian Super-App*

Account: @{user.username}
Tier: {get_user_tier(user.id).upper()}

*Main Features:*
💸 `/send` - Send money (Fee: {FEES[get_user_tier(user.id)]}%)
🛍️ `/market` - Buy & sell goods
🔧 `/gigs` - Find work opportunities
🏠 `/property` - Property listings
📚 `/learn` - Skills & courses
⚙️ `/profile` - Your account & settings

*New Premium Features:*
✅ Lower transaction fees
✅ Unlimited marketplace listings
✅ Priority access to jobs
✅ Advanced analytics

Upgrade: `/premium`
Support: `/help`
"""
    
    keyboard = [
        [
            InlineKeyboardButton("💸 Send Money", callback_data="send_money"),
            InlineKeyboardButton("🛍️ Marketplace", callback_data="marketplace")
        ],
        [
            InlineKeyboardButton("🔧 Find Work", callback_data="gigs"),
            InlineKeyboardButton("📚 Learn Skills", callback_data="learn")
        ],
        [
            InlineKeyboardButton("⚙️ Profile", callback_data="profile"),
            InlineKeyboardButton("⭐ Upgrade", callback_data="upgrade")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium pricing tiers"""
    user_tier = get_user_tier(update.effective_user.id)
    
    message = f"""🚀 *SHEGER Premium Plans*

*Current Plan:* {user_tier.upper()}

*1. SHEGER PRO* - 149 ETB/month
• Transaction fee: 1.5% (vs 2.5% Basic)
• Unlimited marketplace listings
• Priority gig access
• Business profile badge
• Daily limit: 50,000 ETB
• 24h support response

*2. SHEGER ENTERPRISE* - 999 ETB/month
• Transaction fee: 0.8%
• Bulk payment processing
• Custom business portal
• Advanced API access
• Dedicated account manager
• Unlimited transactions
• White-label solutions

*Special Launch Offer:*
First month FREE for all upgrades!
Use code: `SHEGERLAUNCH`

To upgrade, choose a plan below:"""
    
    keyboard = [
        [InlineKeyboardButton("🟢 PRO Monthly - 149 ETB", callback_data="upgrade_pro_monthly")],
        [InlineKeyboardButton("🟢 PRO Yearly - 1,499 ETB (Save 16%)", callback_data="upgrade_pro_yearly")],
        [InlineKeyboardButton("🔵 ENTERPRISE Monthly - 999 ETB", callback_data="upgrade_enterprise_monthly")],
        [InlineKeyboardButton("🔵 ENTERPRISE Yearly - 9,999 ETB (Save 16%)", callback_data="upgrade_enterprise_yearly")],
        [InlineKeyboardButton("📞 Contact Sales", callback_data="contact_sales")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def send_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send money command"""
    user_id = update.effective_user.id
    user_tier = get_user_tier(user_id)
    
    if len(context.args) < 2:
        await update.message.reply_text(
            f"Usage: `/send [amount] [phone_number]`\n"
            f"Example: `/send 500 0961393001`\n\n"
            f"*Your fee:* {FEES[user_tier]}%\n"
            f"*Daily limit:* {'5,000' if user_tier == TIER_BASIC else '50,000' if user_tier == TIER_PRO else 'Unlimited'} ETB",
            parse_mode='Markdown'
        )
        return
    
    try:
        amount = float(context.args[0])
        phone = context.args[1]
        
        # Calculate fee
        fee = calculate_fee(amount, user_id)
        total = amount + fee
        
        # Check if basic user exceeds limit
        if user_tier == TIER_BASIC and amount > 5000:
            await update.message.reply_text(
                "❌ *Limit Exceeded*\n"
                "Basic users can send max 5,000 ETB per day.\n"
                "Upgrade to PRO for 50,000 ETB limit: `/premium`",
                parse_mode='Markdown'
            )
            return
        
        message = f"""✅ *Payment Ready*

To: {phone}
Amount: {amount:,.2f} ETB
Fee ({FEES[user_tier]}%): {fee:,.2f} ETB
Total: {total:,.2f} ETB

*Payment Methods:*
1. telebirr
2. M-Pesa Ethiopia
3. CBE Birr
4. Cash pickup

Choose payment method:"""
        
        keyboard = [
            [
                InlineKeyboardButton("telebirr", callback_data=f"pay_telebirr_{amount}_{phone}"),
                InlineKeyboardButton("M-Pesa", callback_data=f"pay_mpesa_{amount}_{phone}")
            ],
            [
                InlineKeyboardButton("CBE Birr", callback_data=f"pay_cbe_{amount}_{phone}"),
                InlineKeyboardButton("Cash", callback_data=f"pay_cash_{amount}_{phone}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marketplace command"""
    user_id = update.effective_user.id
    
    if not context.args:
        # Show marketplace options
        message = """🛍️ *SHEGER Marketplace*

Buy and sell goods locally!

*Categories:*
• Electronics 📱
• Fashion 👕
• Home & Garden 🏡
• Vehicles 🚗
• Services 🔧
• Property 🏠

*Commands:*
`/market buy [item]` - Search for items
`/market sell [item] [price]` - List item for sale
`/market mine` - Your listings
`/market featured` - Premium listings

You have *unlimited listings* with PRO/Enterprise!
Basic: 3 free listings/month"""
        
        keyboard = [
            [
                InlineKeyboardButton("🛒 Browse", callback_data="browse_market"),
                InlineKeyboardButton("📤 Sell Item", callback_data="sell_item")
            ],
            [
                InlineKeyboardButton("⭐ Featured", callback_data="featured_items"),
                InlineKeyboardButton("📈 My Listings", callback_data="my_listings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Handle subcommands
    subcommand = context.args[0].lower()
    
    if subcommand == "sell":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: `/market sell [item] [price] [location?]`")
            return
        
        # Check if user can list
        if not can_user_list_item(user_id):
            await update.message.reply_text(
                "❌ *Listing Limit Reached*\n"
                "Basic users get 3 free listings per month.\n"
                "Upgrade to PRO for unlimited: `/premium`",
                parse_mode='Markdown'
            )
            return
        
        item = " ".join(context.args[1:-1])
        price = context.args[-1]
        location = context.args[2] if len(context.args) > 3 else "Addis Ababa"
        
        # Record the listing
        if get_user_tier(user_id) == TIER_BASIC:
            users_db[user_id]["free_listings_used"] += 1
        
        listings_db.append({
            "user_id": user_id,
            "item": item,
            "price": price,
            "location": location,
            "timestamp": datetime.now(),
            "premium": is_premium_user(user_id)
        })
        
        await update.message.reply_text(
            f"✅ *Item Listed Successfully!*\n\n"
            f"*Item:* {item}\n"
            f"*Price:* {price} ETB\n"
            f"*Location:* {location}\n\n"
            f"Listings used this month: {users_db[user_id].get('free_listings_used', 0)}/3",
            parse_mode='Markdown'
        )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    user = update.effective_user
    user_id = user.id
    user_data = users_db.get(user_id, {})
    tier = get_user_tier(user_id)
    
    # Calculate stats
    user_transactions = [t for t in transactions_db if t.get("user_id") == user_id]
    user_listings = [l for l in listings_db if l.get("user_id") == user_id]
    
    message = f"""⚙️ *Your SHEGER Profile*

*Account Info:*
Username: @{user.username}
Tier: {tier.upper()}
Joined: {user_data.get('joined', datetime.now()).strftime('%Y-%m-%d')}
Trust Score: {user_data.get('trust_score', 50)}/100

*Usage Stats:*
Transactions: {len(user_transactions)}
Listings: {len(user_listings)}
Balance: {user_data.get('balance', 0):,.2f} ETB

*Subscription:*
Current: {tier.upper()}
Expires: {user_data.get('subscription_end', 'Never') if user_data.get('subscription_end') else 'Never'}

*Actions:*
`/premium` - Upgrade plan
`/balance` - Check balance
`/history` - Transaction history
`/verify` - Verify account
`/help` - Support"""
    
    keyboard = [
        [InlineKeyboardButton("⭐ Upgrade Plan", callback_data="upgrade")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        """🆘 *SHEGER Help Center*

*Quick Commands:*
`/start` - Main menu
`/send [amount] [phone]` - Send money
`/market` - Buy & sell
`/gigs` - Find work
`/premium` - Upgrade account
`/profile` - Your profile
`/help` - This message

*Support Channels:*
📞 Support: @ShegerSupport
🐛 Report Bug: @ShegerBugs
💡 Suggestions: @ShegerIdeas
📰 News: @ShegerNews

*Business Hours:*
Mon-Fri: 8:00 AM - 6:00 PM EAT
Sat: 9:00 AM - 1:00 PM EAT

*Emergency Contact:*
+251 963163418""",
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "upgrade":
        await premium(update, context)
    
    elif data.startswith("upgrade_"):
        # Handle upgrade selections
        parts = data.split("_")
        tier = parts[1]  # pro or enterprise
        period = parts[2]  # monthly or yearly
        
        price = PRICING[tier][period]
        
        await query.edit_message_text(
            f"✅ *Upgrade to {tier.upper()} {period.upper()}*\n\n"
            f"Price: {price:,} ETB\n"
            f"Billing: {period.capitalize()}\n\n"
            f"*Payment Instructions:*\n"
            f"1. Send {price:,} ETB to:\n"
            f"   • telebirr: 0961393001\n"
            f"   • CBE: 1000 645865603\n"
            f"2. Forward payment receipt to @ShegerPayments\n"
            f"3. We'll activate within 1 hour\n\n"
            f"*Use code SHEGERLAUNCH for first month FREE!*",
            parse_mode='Markdown'
        )
    
    elif data == "send_money":
        await query.edit_message_text(
            "💸 *Send Money*\n\n"
            "Usage: `/send [amount] [phone_number]`\n"
            "Example: `/send 500 0961393001`\n\n"
            "We support:\n"
            "• telebirr\n• M-Pesa\n• CBE Birr\n• Cash pickup",
            parse_mode='Markdown'
        )
    
    elif data == "marketplace":
        await market(update, context)

# ======================
# MAIN FUNCTION
# ======================
def main():
    """Start the bot."""
    # Create the Application
    TOKEN = os.getenv("8175654585:AAHkKi9IVa1C0vCknGHQ9ildFgsiwXvmXG4")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("send", send_money))
    app.add_handler(CommandHandler("market", market))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_command))
    
    # Add button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the bot
    logger.info("Starting SHEGER Bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
