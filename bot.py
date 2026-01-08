#!/usr/bin/env python3
"""
SHEGER ET - Ethiopian Super App
FINAL PRODUCTION READY VERSION
"""

import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ======================
# CONFIGURATION - FINAL
# ======================
TELEBIRR = "0961393001"                        # ✅ Your telebirr
CBE = "1000645865603"                          # ✅ Your CBE account
ADMIN_ID = 7714584854                          # ✅ Your Telegram ID
SUPPORT = "https://t.me/ShegerESupport"        # ✅ Created
PAYMENTS = "https://t.me/ShegerPayments"       # ✅ Created  
SALES = "https://t.me/ShegerESales"            # ✅ Created
NEWS = "https://t.me/ShegeErNews"              # ✅ Created

BOT_NAME = "SHEGER ET"
BOT_USERNAME = "@ShegerETBot"
BOT_SLOGAN = "Ethiopia's All-in-One Super App"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Data storage
data = {"payments": [], "pending": {}, "users": {}}

def save():
    try:
        with open("sheger_data.json", "w") as f:
            json.dump(data, f, indent=2)
    except:
        pass

def load():
    global data
    try:
        with open("sheger_data.json", "r") as f:
            data = json.load(f)
    except:
        data = {"payments": [], "pending": {}, "users": {}}
        save()

load()

# ======================
# HELPER FUNCTIONS
# ======================
def get_plan(user_id):
    """Get user's current plan"""
    user_id_str = str(user_id)
    for payment in data["payments"][::-1]:
        if str(payment["user_id"]) == user_id_str:
            pay_date = datetime.fromisoformat(payment["time"])
            if datetime.now() - pay_date <= timedelta(days=30):
                return payment["plan"]
    return "basic"

def get_fee(user_id):
    """Get user's transaction fee"""
    plan = get_plan(user_id)
    return {"basic": 2.5, "pro": 1.5, "business": 0.8}[plan]

# ======================
# COMMANDS
# ======================
async def start(update: Update, context):
    user = update.effective_user
    plan = get_plan(user.id)
    fee = get_fee(user.id)
    
    keyboard = [
        [InlineKeyboardButton(f"⭐ {plan.upper()} PLAN", callback_data="my_plan"),
         InlineKeyboardButton("🚀 UPGRADE", callback_data="premium")],
        [InlineKeyboardButton("💸 SEND MONEY", callback_data="send"),
         InlineKeyboardButton("🛍️ MARKETPLACE", callback_data="market")],
        [InlineKeyboardButton("🔧 FIND WORK", callback_data="jobs"),
         InlineKeyboardButton("🏠 PROPERTIES", callback_data="property")],
        [InlineKeyboardButton("📞 SUPPORT", url=f"https://t.me/{SUPPORT[1:]}"),
         InlineKeyboardButton("📊 STATS", callback_data="stats")]
    ]
    
    text = f"""🌟 *{BOT_NAME}* 🇪🇹
*{BOT_SLOGAN}*

Welcome @{user.username}!

*Your Plan:* {plan.upper()}
*Your Fee:* {fee}%

*ALL SERVICES:*
• 💸 Send/Receive Money
• 🛍️ Buy/Sell Marketplace
• 🔧 Jobs & Hiring
• 🏠 Properties & Land
• 🚗 Transport & Delivery
• 📱 Mobile & Airtime
• 🏥 Health Services
• 📚 Education

*UPGRADE TO PRO:*
• 1.5% fee (Save 40%)
• Unlimited listings
• Priority support
• Business tools

*Ready to explore?*"""
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def premium(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🚀 PRO - 149 ETB/month", callback_data="upgrade_pro")],
        [InlineKeyboardButton("🏢 BUSINESS - 999 ETB/month", callback_data="upgrade_business")],
        [InlineKeyboardButton("📞 CONTACT SALES", callback_data="contact")]
    ]
    
    text = f"""🚀 *{BOT_NAME} PREMIUM*

*1. SHEGER PRO* - 149 ETB/month
• Fee: 1.5% (Basic: 2.5%)
• Unlimited listings
• Priority support
• Business badge
• 50K ETB daily limit

*2. SHEGER BUSINESS* - 999 ETB/month
• Fee: 0.8% (Lowest!)
• Bulk payments
• Business dashboard
• Dedicated manager
• API access

*🎁 LAUNCH OFFER:*
First month FREE!
Code: *SHEGERLAUNCH*

*💯 7-day money back guarantee*"""
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_cmd(update: Update, context):
    text = f"""🆘 *{BOT_NAME} HELP*

*Commands:*
`/start` - Main menu
`/premium` - Upgrade
`/help` - This message

*Support:*
📞 {SUPPORT}
💰 {PAYMENTS}
🏢 {SALES}
📰 {NEWS}

*Contact:* +251 963 163 418
*24/7 support available*"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    
    if query.data == "premium":
        await premium(update, context)
    
    elif query.data == "upgrade_pro":
        data["pending"][str(user_id)] = {
            "username": username,
            "name": user.full_name,
            "plan": "pro",
            "amount": 149,
            "time": datetime.now().isoformat()
        }
        save()
        
        text = f"""✅ *SHEGER PRO SELECTED*

💰 *149 ETB/month*
👤 @{username}
🆔 `{user_id}`

*PAYMENT:*
1. Send *149 ETB* to:
   • telebirr: `{TELEBIRR}`
   • CBE: `{CBE}`

2. Forward receipt to: {PAYMENTS}
   Include: *PRO-{user_id}*

3. Activation in 30 minutes!

*OFFER:* First month FREE!
Code: *SHEGERLAUNCH*

*Questions?* {SUPPORT}"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        logger.info(f"💸 PRO selected: {user_id}")
    
    elif query.data == "upgrade_business":
        await query.edit_message_text(
            f"""🏢 *SHEGER BUSINESS SELECTED*

💰 *999 ETB/month*

Contact {SALES} for:
• Custom invoice
• Business solutions
• Bulk payments

Or send to:
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

Include: *BUSINESS-{user_id}*""",
            parse_mode='Markdown'
        )
    
    elif query.data == "my_plan":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        await query.edit_message_text(f"⭐ *YOUR PLAN:* {plan.upper()}\n💸 *FEE:* {fee}%", parse_mode='Markdown')
    
    elif query.data == "contact":
        await query.edit_message_text(f"📞 *CONTACT SALES*\n\n{SALES}\nsales@sheger.et\n+251 963 163 418", parse_mode='Markdown')

# ======================
# ADMIN COMMANDS
# ======================
async def revenue(update: Update, context):
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only.")
        return
    
    load()
    total = sum(p["amount"] for p in data["payments"])
    
    text = f"""💰 *{BOT_NAME} REVENUE*

Total: {total:,} ETB
Customers: {len(data["payments"])}
Pending: {len(data["pending"])}

*Recent:*
"""
    for p in data["payments"][-5:][::-1]:
        time = datetime.fromisoformat(p["time"]).strftime("%b %d")
        text += f"• {p['plan'].upper()} - {p['amount']:,} ETB - {time}\n"
    
    if total == 0:
        text += "\n🎯 *Ready for first customer!*"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def verify(update: Update, context):
    if update.effective_user.id != 7714584854:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/verify [user_id] [amount=149]`")
        return
    
    user_id = context.args[0]
    amount = float(context.args[1]) if len(context.args) > 1 else 149.0
    plan = "pro"
    
    load()
    
    if user_id in data["pending"]:
        pending = data["pending"].pop(user_id)
        
        payment = {
            "user_id": user_id,
            "username": pending["username"],
            "plan": plan,
            "amount": amount,
            "time": datetime.now().isoformat()
        }
        
        data["payments"].append(payment)
        
        # Add user
        if user_id not in data["users"]:
            data["users"][user_id] = {
                "username": pending["username"],
                "joined": datetime.now().isoformat(),
                "plan": plan,
                "total": amount
            }
        
        save()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"""🎉 *SHEGER PRO ACTIVATED!*

Welcome to SHEGER PRO! Your account is now active.

• Fee: 1.5% (was 2.5%)
• Unlimited listings
• Priority support
• Active 30 days

Use `/start` to explore! 🚀"""
            )
            notified = True
        except:
            notified = False
        
        total = sum(p["amount"] for p in data["payments"])
        await update.message.reply_text(
            f"✅ *VERIFIED!*\n\n"
            f"User: {user_id}\n"
            f"Plan: PRO\n"
            f"Amount: {amount:,} ETB\n"
            f"Notified: {'✅' if notified else '❌'}\n\n"
            f"Total Revenue: {total:,} ETB",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ No pending payment for {user_id}")

async def pending(update: Update, context):
    if update.effective_user.id != 7714584854:
        return
    
    load()
    
    if not data["pending"]:
        await update.message.reply_text("📭 No pending payments.")
        return
    
    text = "⏳ *PENDING PAYMENTS*\n\n"
    total = 0
    
    for user_id, details in data["pending"].items():
        mins = (datetime.now() - datetime.fromisoformat(details["time"])).seconds // 60
        text += f"• {user_id}: {details['plan'].upper()} - {details['amount']:,} ETB ({mins}m ago)\n"
        total += details['amount']
    
    text += f"\n*Total:* {len(data['pending'])} users, {total:,} ETB"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def stats(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    
    load()
    total = sum(p["amount"] for p in data["payments"])
    pro = sum(1 for p in data["payments"] if p["plan"] == "pro")
    business = sum(1 for p in data["payments"] if p["plan"] == "business")
    
    text = f"""📊 *{BOT_NAME} STATS*

*Financial:*
Total Revenue: {total:,} ETB
Pending: {len(data["pending"])}
Avg/Customer: {total/max(len(data["payments"]), 1):,.0f} ETB

*Customers:*
PRO: {pro} users
BUSINESS: {business} users
Total: {len(data["payments"])} users

*Projections:*
Daily Goal: 1,490 ETB
Weekly Goal: 7,450 ETB
Monthly Goal: 29,800 ETB

*Status:* 🟢 LIVE
*Bot:* {BOT_USERNAME}
*Founder:* {ADMIN_ID}"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# MAIN
# ======================
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not set!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("help", help_cmd))
    
    # Admin commands
    app.add_handler(CommandHandler("revenue", revenue))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("stats", stats))
    
    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("=" * 60)
    logger.info(f"🚀 {BOT_NAME} STARTING")
    logger.info(f"🤖 {BOT_USERNAME}")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info("💰 READY FOR REVENUE!")
    logger.info("=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
