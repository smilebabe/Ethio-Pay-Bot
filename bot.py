#!/usr/bin/env python3
"""
SHEGER ET - Ethiopian Super App
FINAL PRODUCTION READY VERSION - ALL FIXES APPLIED
"""

import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ======================
# CONFIGURATION - FINAL & CORRECT
# ======================
TELEBIRR = "0961393001"            # ✅ Your telebirr
CBE = "1000645865603"              # ✅ Your CBE account
ADMIN_ID = 7714584854              # ✅ Your Telegram ID

# CORRECTED CHANNELS (Use @username format)
SUPPORT = "@ShegerESupport"        # ✅ Your support channel
PAYMENTS = "@ShegerPayments"       # ✅ Your payments channel  
SALES = "@ShegerESales"            # ✅ Your sales channel
NEWS = "@ShegeErNews"              # ✅ Your news channel

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
    except Exception as e:
        logger.error(f"Save error: {e}")

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
        [InlineKeyboardButton("📞 SUPPORT", url=f"https://t.me/ShegerESupport"),
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
`/premium` - Upgrade plans
`/help` - This message

*Support Channels:*
📞 Customer Support: {SUPPORT}
💰 Payment Issues: {PAYMENTS}
🏢 Business Sales: {SALES}
📰 News & Updates: {NEWS}

*Contact Information:*
📱 Phone: +251 963 163 418
📧 Email: support@sheger.et
⏰ 24/7 support available

*Need immediate help?*
Message {SUPPORT} or call +251 963 163 418"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    
    # Handle button clicks
    if query.data == "premium":
        # FIXED: Premium upgrade menu
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
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "upgrade_pro":
        # Track pending payment
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
👤 User: @{username}
🆔 Your ID: `{user_id}`

*📋 PAYMENT INSTRUCTIONS:*

1. Send *149 ETB* to:
   • telebirr: `{TELEBIRR}`
   • CBE Bank: `{CBE}`

2. Forward payment receipt to: {PAYMENTS}
   *IMPORTANT:* Include this code: `PRO-{user_id}`

3. We'll activate your account within 30 minutes!

*🎁 LAUNCH SPECIAL:*
First month FREE with code: *SHEGERLAUNCH*

*Need help?* Contact {SUPPORT}
*Payment questions?* {PAYMENTS}"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        logger.info(f"💰 PRO upgrade initiated: {user_id} (@{username})")
    
    elif query.data == "upgrade_business":
        text = f"""🏢 *SHEGER BUSINESS SELECTED*

💰 *999 ETB/month*

*For business inquiries, contact:* {SALES}

*Or send payment to:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Include reference:* `BUSINESS-{user_id}`

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
    
    elif query.data == "my_plan":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        if plan == "basic":
            benefits = "• 2.5% transaction fee\n• 5 free listings/month\n• Standard support"
            action = "Upgrade to PRO for better features!"
        elif plan == "pro":
            benefits = "• 1.5% transaction fee (Save 40%!)\n• Unlimited listings\n• Priority support\n• Business badge"
            action = "You're on the best plan! 🎉"
        else:
            benefits = "• 0.8% transaction fee (Lowest rate!)\n• Bulk payment processing\n• Business dashboard\n• Dedicated manager"
            action = "Thank you for being a business customer! 🏢"
        
        text = f"""⭐ *YOUR {BOT_NAME} PLAN*

*Current Plan:* {plan.upper()}
*Transaction Fee:* {fee}%
*Status:* Active ✅

*Plan Benefits:*
{benefits}

{action}

*Need to change your plan?*
Contact {SUPPORT}"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "send":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        text = f"""💸 *SEND MONEY WITH {BOT_NAME}*

*Your current fee:* {fee}% ({plan.upper()} plan)

*Send to any Ethiopian:*
• Phone number (telebirr/M-Pesa)
• Bank account
• {BOT_NAME} username
• Email address

*Supported Networks:*
• telebirr • M-Pesa Ethiopia
• CBE Birr • All major banks
• Cash pickup locations

*Features Coming Soon:*
• Instant transfers (seconds)
• Scheduled payments
• Bulk payments
• Currency conversion
• Payment reminders

*Security:*
• End-to-end encryption
• Two-factor authentication
• Fraud detection
• Money-back guarantee

*Status:* 🚧 In Development
Upgrade to PRO for early access!"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "market":
        plan = get_plan(user_id)
        
        if plan == "basic":
            listings = "5 free listings per month"
        else:
            listings = "Unlimited listings"
        
        text = f"""🛍️ *{BOT_NAME} MARKETPLACE*

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
• {"Priority placement" if plan != "basic" else "Standard placement"}
• {"Advanced analytics" if plan == "business" else "Basic analytics"}

*Security Features:*
• Escrow protection
• Verified sellers
• Buyer protection
• Rating system
• Dispute resolution

*Start buying or selling today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "jobs":
        text = f"""🔧 *FIND WORK ON {BOT_NAME}*

*Job Categories:*
• 💻 Tech & Programming
• 🏗️ Construction & Labor
• 🚚 Driving & Delivery
• 👨‍🏫 Teaching & Tutoring
• 🏥 Healthcare
• 🍽️ Hospitality
• 📊 Administration
• 🛠️ Skilled Trades
• 🎨 Creative & Design
• 📞 Customer Service

*For Job Seekers:*
• Browse thousands of jobs
• Apply directly through bot
• Get job alerts
• Build your profile
• Get hired faster

*For Employers:*
• Post jobs for FREE
• Reach qualified candidates
• Manage applications
• Hire with confidence

*Start your job search or post a job today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "property":
        text = f"""🏠 *PROPERTIES ON {BOT_NAME}*

*Find Your Perfect Property:*
• 🏡 Houses for Rent/Sale
• 🏢 Apartments & Condos
• 🏪 Commercial Spaces
• 🗺️ Land & Plots
• 🏖️ Vacation Rentals
• 🏨 Hotel & Guest Houses
• 🏭 Industrial Properties
• 🏛️ Office Spaces

*Verified Properties Only:*
• All listings verified
• Authentic photos
• Accurate location data
• Price transparency
• Owner/Agent verification

*Features:*
• Advanced search filters
• Save favorite properties
• Price alerts
• Virtual tours (Coming soon)
• Mortgage calculator (Coming soon)

*Find your dream home or investment property today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "contact":
        text = f"""📞 *CONTACT {BOT_NAME} SALES*

*For Business & Enterprise Inquiries:*
• Custom pricing for volume
• API integration
• White-label solutions
• Bulk user onboarding
• Dedicated support
• Custom feature development

*Contact Information:*
Telegram: {SALES}
Email: sales@sheger.et
Phone: +251 963 163 418
Website: sheger.et (Coming Soon)

*Office Hours:*
Monday - Friday: 8:00 AM - 6:00 PM EAT
Saturday: 9:00 AM - 1:00 PM EAT

*What to include when contacting:*
1. Your business name
2. Estimated monthly volume
3. Specific needs/requirements
4. Contact person details
5. Preferred contact method

*We respond within 1 business day!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "stats":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        # Calculate savings if PRO/BUSINESS
        if plan != "basic":
            typical_monthly = 10000  # Assume 10,000 ETB monthly
            basic_fee = typical_monthly * 0.025
            current_fee = typical_monthly * (fee/100)
            monthly_savings = basic_fee - current_fee
            savings_text = f"*Monthly Savings:* ~{monthly_savings:,.0f} ETB"
        else:
            savings_text = "*Upgrade to start saving!*"
        
        text = f"""📊 *YOUR {BOT_NAME} STATS*

*Account Information:*
👤 Username: @{username}
🆔 User ID: `{user_id}`
⭐ Current Plan: {plan.upper()}
💸 Transaction Fee: {fee}%

{savings_text}

*Features Available:*
{"✓ Unlimited listings" if plan != "basic" else "✓ 5 free listings/month"}
{"✓ Priority support" if plan != "basic" else "✓ Standard support"}
{"✓ Business tools" if plan != "basic" else "✓ Basic tools"}
{"✓ Advanced analytics" if plan == "business" else "✓ Basic analytics"}

*Ready to upgrade?*
Tap UPGRADE for better features!"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
# ======================
# ADMIN COMMANDS
# ======================
async def revenue(update: Update, context):
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    load()
    total = sum(p["amount"] for p in data["payments"])
    
    text = f"""💰 *{BOT_NAME} REVENUE DASHBOARD*

*Total Revenue:* {total:,} ETB
*Completed Payments:* {len(data["payments"])}
*Pending Payments:* {len(data["pending"])}

*Recent Transactions:*
"""
    
    if data["payments"]:
        for i, p in enumerate(data["payments"][-5:][::-1], 1):
            time = datetime.fromisoformat(p["time"]).strftime("%b %d %H:%M")
            text += f"{i}. {p['plan'].upper()} - {p['amount']:,} ETB - {time}\n"
    else:
        text += "No transactions yet.\n"
    
    if data["pending"]:
        text += f"\n*⏳ Pending:* {len(data['pending'])} payments\n"
        pending_total = sum(d["amount"] for d in data["pending"].values())
        text += f"Potential revenue: {pending_total:,} ETB"
    
    if total == 0:
        text += "\n🎯 *Ready for your first customer!*\nTime to start marketing! 🚀"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def verify(update: Update, context):
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/verify [user_id] [amount=149]`\n"
            "Example: `/verify 123456789 149`\n"
            "Example: `/verify 123456789 business 999`"
        )
        return
    
    user_id = context.args[0]
    
    # Get amount and plan
    if len(context.args) > 2:
        plan = context.args[1]
        amount = float(context.args[2])
    elif len(context.args) > 1:
        try:
            amount = float(context.args[1])
            plan = "pro"
        except:
            plan = context.args[1]
            amount = 149.0 if plan == "pro" else 999.0
    else:
        amount = 149.0
        plan = "pro"
    
    load()
    
    if user_id in data["pending"]:
        # Move from pending to completed
        pending = data["pending"].pop(user_id)
        
        payment = {
            "user_id": user_id,
            "username": pending["username"],
            "plan": plan,
            "amount": amount,
            "time": datetime.now().isoformat()
        }
        
        data["payments"].append(payment)
        
        # Add/update user
        if user_id not in data["users"]:
            data["users"][user_id] = {
                "username": pending["username"],
                "joined": datetime.now().isoformat(),
                "plan": plan,
                "total": amount
            }
        else:
            data["users"][user_id]["plan"] = plan
            data["users"][user_id]["total"] = data["users"][user_id].get("total", 0) + amount
        
        save()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"""🎉 *WELCOME TO {BOT_NAME} {plan.upper()}!*

Your payment has been verified and your account is now active.

*Plan Benefits:*
• Transaction fee: {"1.5%" if plan == "pro" else "0.8%"}
• Unlimited listings in all categories
• Priority 24/7 support
• Active for 30 days

*Get Started:*
1. Use `/start` to explore features
2. Try marketplace, properties, jobs
3. Contact {SUPPORT} for help

Thank you for choosing {BOT_NAME}! 🚀"""
            )
            notified = True
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
            notified = False
        
        total_revenue = sum(p["amount"] for p in data["payments"])
        
        await update.message.reply_text(
            f"✅ *PAYMENT VERIFIED!*\n\n"
            f"*Customer Details:*\n"
            f"👤 User: {user_id}\n"
            f"📛 Username: @{pending['username']}\n"
            f"🎫 Plan: {plan.upper()}\n"
            f"💰 Amount: {amount:,} ETB\n"
            f"📧 Notified: {'✅' if notified else '❌'}\n\n"
            f"*Business Metrics:*\n"
            f"Total Revenue: {total_revenue:,} ETB\n"
            f"Active Customers: {len(data['users'])}\n"
            f"Pending Payments: {len(data['pending'])}",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Payment verified: {user_id} - {plan} - {amount} ETB")
    
    else:
        await update.message.reply_text(
            f"❌ *No Pending Payment Found*\n\n"
            f"User ID: {user_id}\n\n"
            f"*Possible Reasons:*\n"
            f"1. User hasn't initiated payment\n"
            f"2. Payment already verified\n"
            f"3. Different user ID\n\n"
            f"Check: `/pending`\n"
            f"Or add manually: `/verify {user_id} {plan} {amount}`",
            parse_mode='Markdown'
        )

async def pending(update: Update, context):
    if update.effective_user.id != 7714584854:
        return
    
    load()
    
    if not data["pending"]:
        await update.message.reply_text("📭 No pending payments. Time to get more customers! 🚀")
        return
    
    text = "⏳ *PENDING PAYMENTS*\n\n"
    total = 0
    
    for user_id, details in data["pending"].items():
        mins = (datetime.now() - datetime.fromisoformat(details["time"])).seconds // 60
        hours = mins // 60
        time_text = f"{hours}h {mins%60}m" if hours > 0 else f"{mins}m"
        
        text += f"• {user_id} (@{details['username']}): {details['plan'].upper()} - {details['amount']:,} ETB ({time_text} ago)\n"
        total += details['amount']
    
    text += f"\n*Summary:*\n"
    text += f"Total Pending: {len(data['pending'])} customers\n"
    text += f"Total Amount: {total:,} ETB\n"
    text += f"Average: {total/len(data['pending']):,.0f} ETB/customer"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def stats(update: Update, context):
    if update.effective_user.id != 7714584854:
        return
    
    load()
    
    total = sum(p["amount"] for p in data["payments"])
    pro = sum(1 for p in data["payments"] if p["plan"] == "pro")
    business = sum(1 for p in data["payments"] if p["plan"] == "business")
    
    # Monthly calculation
    current_month = datetime.now().month
    monthly = sum(
        p["amount"] for p in data["payments"] 
        if datetime.fromisoformat(p["time"]).month == current_month
    )
    
    text = f"""📊 *{BOT_NAME} BUSINESS STATISTICS*

*Financial Performance:*
Total Revenue: {total:,} ETB
Current Month: {monthly:,} ETB
Pending Revenue: {sum(d["amount"] for d in data["pending"].values()):,} ETB
Average/Customer: {total/max(len(data["payments"]), 1):,.0f} ETB

*Customer Metrics:*
Total Customers: {len(data["payments"])}
PRO Customers: {pro}
BUSINESS Customers: {business}
Pending Signups: {len(data["pending"])}

*Projections (Based on Current Rate):*
Daily: {(monthly/30):,.0f} ETB
Weekly: {(monthly/4.3):,.0f} ETB
Monthly: {monthly:,} ETB
Annual: {monthly*12:,} ETB

*Platform Health:*
🟢 Bot Status: ONLINE
🤖 Username: {BOT_USERNAME}
👑 Admin ID: {ADMIN_ID}
📅 Data Since: {min((datetime.fromisoformat(p["time"]) for p in data["payments"]), default=datetime.now()).strftime("%B %d, %Y")}

*Next Milestones:*
🎯 10 Customers: {1490 - total:,} ETB to go
🎯 50 Customers: {7450 - total:,} ETB to go
🎯 100 Customers: {14900 - total:,} ETB to go

*Keep growing! Every customer brings you closer to success!* 🚀"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# MAIN FUNCTION
# ======================
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not set in Railway Variables!")
        logger.error("💡 Add it in Railway → Variables")
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
    
    # Button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("=" * 70)
    logger.info(f"🚀 {BOT_NAME} - FINAL PRODUCTION VERSION")
    logger.info(f"🌟 {BOT_SLOGAN}")
    logger.info(f"🤖 Bot: {BOT_USERNAME}")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"📱 telebirr: {TELEBIRR}")
    logger.info(f"🏦 CBE: {CBE}")
    logger.info(f"📞 Support: {SUPPORT}")
    logger.info(f"💰 Payments: {PAYMENTS}")
    logger.info("✅ ALL SYSTEMS READY FOR REVENUE!")
    logger.info("=" * 70)
    
    app.run_polling()

if __name__ == "__main__":
    main()
