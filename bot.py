#!/usr/bin/env python3
"""
SHEGER ET - Ethiopian Super App
FINAL PRODUCTION READY VERSION WITH DATABASE
"""

import os
import json
import logging
import sqlite3
import shutil
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

# ======================
# DATABASE CONFIGURATION
# ======================
DATABASE_PATH = os.getenv("DATABASE_URL", "sheger_et.db")
BACKUP_DIR = "sheger_backups"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================
# DATABASE INITIALIZATION
# ======================
def init_database():
    """Initialize SQLite database for Railway"""
    try:
        # Create backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Enable WAL mode for better performance
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                plan TEXT DEFAULT 'basic',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_spent REAL DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                plan TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                reference_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Database initialized: {DATABASE_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

# Initialize database on startup
init_database()

# ======================
# DATABASE HELPER FUNCTIONS
# ======================
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_create_user(user_id, username, full_name):
    """Create or update user in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute('''
                UPDATE users SET username = ?, full_name = ? WHERE user_id = ?
            ''', (username, full_name, user_id))
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, plan)
                VALUES (?, ?, ?, 'basic')
            ''', (user_id, username, full_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return False

def db_create_payment(user_id, username, plan, amount):
    """Create payment record in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        reference_code = f"{plan.upper()}-{user_id}-{int(datetime.now().timestamp())}"
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO payments (user_id, username, plan, amount, reference_code, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, plan, amount, reference_code, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💰 Payment created: {user_id} - {plan} - {amount}")
        return reference_code
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return None

def db_verify_payment(user_id, amount=None, plan=None):
    """Verify payment in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest pending payment
        cursor.execute('''
            SELECT * FROM payments 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        
        payment = cursor.fetchone()
        if not payment:
            return False, "No pending payment found"
        
        actual_plan = plan or payment['plan']
        actual_amount = amount or payment['amount']
        
        # Update payment status
        cursor.execute('''
            UPDATE payments 
            SET status = 'verified', 
                verified_at = CURRENT_TIMESTAMP,
                plan = ?,
                amount = ?
            WHERE id = ?
        ''', (actual_plan, actual_amount, payment['id']))
        
        # Update user plan and total spent
        cursor.execute('''
            UPDATE users 
            SET plan = ?, 
                total_spent = total_spent + ?
            WHERE user_id = ?
        ''', (actual_plan, actual_amount, user_id))
        
        conn.commit()
        conn.close()
        
        return True, f"Payment verified! User upgraded to {actual_plan.upper()}"
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return False, f"Error: {str(e)}"

def db_get_plan(user_id):
    """Get user's current plan from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for active verified payments
        cursor.execute('''
            SELECT plan, verified_at FROM payments 
            WHERE user_id = ? AND status = 'verified'
            ORDER BY verified_at DESC LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            verified_date = datetime.fromisoformat(result['verified_at'])
            if datetime.now() - verified_date <= timedelta(days=30):
                conn.close()
                return result['plan']
        
        # Get user's default plan
        cursor.execute('SELECT plan FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        conn.close()
        
        return user_row['plan'] if user_row else 'basic'
        
    except Exception as e:
        logger.error(f"Error getting plan for {user_id}: {e}")
        return 'basic'

# ======================
# BACKUP FUNCTIONS
# ======================
def create_backup():
    """Create manual backup of database"""
    try:
        if not os.path.exists(DATABASE_PATH):
            return False, "Database file not found"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
        
        shutil.copy2(DATABASE_PATH, backup_file)
        
        # Keep only last 10 backups
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_")])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
        
        return True, backup_file
    except Exception as e:
        return False, str(e)

def list_backups():
    """List all available backups"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return []
        
        backups = []
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("backup_") and filename.endswith(".db"):
                filepath = os.path.join(BACKUP_DIR, filename)
                size = os.path.getsize(filepath)
                modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                backups.append({
                    'name': filename,
                    'size': size,
                    'modified': modified,
                    'path': filepath
                })
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return []

# ======================
# COMPATIBILITY LAYER (KEEPS OLD JSON FUNCTIONS WORKING)
# ======================
# This ensures your existing code continues to work
data = {"payments": [], "pending": {}, "users": {}}

def save():
    """Save to JSON (for backward compatibility)"""
    try:
        with open("sheger_data.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

def load():
    """Load from JSON (for backward compatibility)"""
    global data
    try:
        with open("sheger_data.json", "r") as f:
            data = json.load(f)
    except:
        data = {"payments": [], "pending": {}, "users": {}}
        save()

load()

def get_plan(user_id):
    """Get user plan - tries database first, falls back to JSON"""
    # Try database first
    db_plan = db_get_plan(user_id)
    
    # Also update JSON for compatibility
    user_id_str = str(user_id)
    for payment in data["payments"][::-1]:
        if str(payment["user_id"]) == user_id_str:
            pay_date = datetime.fromisoformat(payment["time"])
            if datetime.now() - pay_date <= timedelta(days=30):
                return payment["plan"]
    
    return db_plan  # Return database result

def get_fee(user_id):
    """Get user's transaction fee"""
    plan = get_plan(user_id)
    return {"basic": 2.5, "pro": 1.5, "business": 0.8}[plan]

# ======================
# EXISTING COMMANDS (UNCHANGED)
# ======================
async def start(update: Update, context):
    user = update.effective_user
    plan = get_plan(user.id)
    fee = get_fee(user.id)
    
    # Create user in database
    db_create_user(user.id, user.username, user.full_name)
    
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
        # Create payment in database
        reference_code = db_create_payment(user_id, username, "pro", 149)
        
        # Also update JSON for compatibility
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
📋 Reference: `{reference_code or f'PRO-{user_id}'}`

*📋 PAYMENT INSTRUCTIONS:*

1. Send *149 ETB* to:
   • telebirr: `{TELEBIRR}`
   • CBE Bank: `{CBE}`

2. Forward payment receipt to: {PAYMENTS}
   *IMPORTANT:* Include reference code

3. We'll activate your account within 30 minutes!

*🎁 LAUNCH SPECIAL:*
First month FREE with code: *SHEGERLAUNCH*

*Need help?* Contact {SUPPORT}
*Payment questions?* {PAYMENTS}"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        logger.info(f"💰 PRO upgrade initiated: {user_id} (@{username})")
    
    elif query.data == "upgrade_business":
        # Create payment in database
        reference_code = db_create_payment(user_id, username, "business", 999)
        
        text = f"""🏢 *SHEGER BUSINESS SELECTED*

💰 *999 ETB/month*
👤 User: @{username}
🆔 Your ID: `{user_id}`
📋 Reference: `{reference_code or f'BUSINESS-{user_id}'}`

*For business inquiries, contact:* {SALES}

*Or send payment to:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Include reference code in payment*

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
        
        if plan != "basic":
            typical_monthly = 10000
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
# ENHANCED ADMIN COMMANDS (WITH DATABASE SUPPORT)
# ======================
async def revenue(update: Update, context):
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Get data from database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total revenue from database
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified'")
        db_total = cursor.fetchone()[0] or 0
        
        # Get database stats
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'verified'")
        db_verified = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        db_pending = cursor.fetchone()[0]
        
        conn.close()
        
        # Also load JSON for backward compatibility
        load()
        json_total = sum(p["amount"] for p in data["payments"])
        
        # Use whichever is higher (database should have latest)
        total = max(db_total, json_total)
        
        text = f"""💰 *{BOT_NAME} REVENUE DASHBOARD*

*Total Revenue:* {total:,} ETB
*Completed Payments:* {db_verified}
*Pending Payments:* {db_pending}

*Data Source:* {'Database ✅' if db_total > 0 else 'JSON (migrating)'}

*Recent Transactions (from database):*
"""
        
        # Get recent transactions from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username 
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'verified'
            ORDER BY p.verified_at DESC LIMIT 5
        ''')
        
        recent = cursor.fetchall()
        conn.close()
        
        if recent:
            for i, payment in enumerate(recent, 1):
                time = datetime.fromisoformat(payment['verified_at']).strftime("%b %d %H:%M")
                text += f"{i}. {payment['plan'].upper()} - {payment['amount']:,} ETB - @{payment['username']} - {time}\n"
        else:
            text += "No database transactions yet.\n"
        
        if total == 0:
            text += "\n🎯 *Ready for your first customer!*\nTime to start marketing! 🚀"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in revenue command: {e}")
        # Fall back to original JSON method
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
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def verify(update: Update, context):
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/verify [user_id] [amount=149] [plan=pro]`\n"
            "Example: `/verify 123456789 149 pro`\n"
            "Example: `/verify 123456789 business 999`"
        )
        return
    
    user_id = context.args[0]
    
    # Parse arguments
    amount = 149.0
    plan = "pro"
    
    if len(context.args) >= 2:
        try:
            amount = float(context.args[1])
        except:
            await update.message.reply_text("❌ Invalid amount format")
            return
    
    if len(context.args) >= 3:
        plan = context.args[2].lower()
        if plan not in ["pro", "business"]:
            await update.message.reply_text("❌ Invalid plan. Use 'pro' or 'business'")
            return
    
    # Try database verification first
    db_success, db_message = db_verify_payment(user_id, amount, plan)
    
    if db_success:
        # Also update JSON for compatibility
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
        
        await update.message.reply_text(
            f"✅ *PAYMENT VERIFIED!*\n\n"
            f"{db_message}\n"
            f"💰 Amount: {amount:,.0f} ETB\n"
            f"📧 User notified: {'✅' if notified else '❌'}\n\n"
            f"*Data saved to database for persistence.*",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Payment verified via database: {user_id} - {plan} - {amount} ETB")
    
    else:
        # Fall back to JSON method if database fails
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
            
            # Notify user (same as above)
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
            
            logger.info(f"✅ Payment verified via JSON: {user_id} - {plan} - {amount} ETB")
        
        else:
            await update.message.reply_text(
                f"❌ *No Pending Payment Found*\n\n"
                f"User ID: {user_id}\n\n"
                f"*Tried both database and JSON*\n\n"
                f"Check: `/pending`\n"
                f"Or add manually: `/verify {user_id} {plan} {amount}`",
                parse_mode='Markdown'
            )

async def pending(update: Update, context):
    if update.effective_user.id != 7714584854:
        return
    
    # Try database first
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, u.username 
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
        ''')
        
        db_pending = cursor.fetchall()
        conn.close()
        
        if db_pending:
            text = "⏳ *PENDING PAYMENTS (Database)*\n\n"
            total = 0
            
            for payment in db_pending:
                created_time = datetime.fromisoformat(payment['created_at'])
                mins_ago = (datetime.now() - created_time).seconds // 60
                hours_ago = mins_ago // 60
                
                if hours_ago > 0:
                    time_text = f"{hours_ago}h {mins_ago%60}m ago"
                else:
                    time_text = f"{mins_ago}m ago"
                
                username = payment['username'] or f"user_{payment['user_id']}"
                text += f"• `{payment['user_id']}` (@{username}): {payment['plan'].upper()} - {payment['amount']:,} ETB ({time_text})\n"
                text += f"  Reference: `{payment['reference_code']}`\n\n"
                total += payment['amount']
            
            text += f"\n*Summary:*\n"
            text += f"Total Pending: {len(db_pending)} customers\n"
            text += f"Total Amount: {total:,} ETB\n"
            text += f"Average: {total/len(db_pending):,.0f} ETB/customer\n\n"
            text += f"*Verify with:* `/verify USER_ID AMOUNT PLAN`"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            return
            
    except Exception as e:
        logger.error(f"Error getting pending from database: {e}")
    
    # Fall back to JSON
    load()
    
    if not data["pending"]:
        await update.message.reply_text("📭 No pending payments. Time to get more customers! 🚀")
        return
    
    text = "⏳ *PENDING PAYMENTS (JSON)*\n\n"
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
    
    # Get stats from database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total revenue
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified'")
        total = cursor.fetchone()[0] or 0
        
        # Plan distribution
        cursor.execute('''
            SELECT plan, COUNT(*) as count, SUM(amount) as revenue
            FROM payments 
            WHERE status = 'verified'
            GROUP BY plan
        ''')
        
        plan_stats = cursor.fetchall()
        pro = business = 0
        for stat in plan_stats:
            if stat['plan'] == 'pro':
                pro = stat['count']
            elif stat['plan'] == 'business':
                business = stat['count']
        
        # Monthly revenue
        current_month = datetime.now().month
        cursor.execute('''
            SELECT SUM(amount) as monthly
            FROM payments 
            WHERE status = 'verified' AND strftime('%m', verified_at) = ?
        ''', (f"{current_month:02d}",))
        
        monthly_row = cursor.fetchone()
        monthly = monthly_row['monthly'] if monthly_row and monthly_row['monthly'] else 0
        
        # Pending revenue
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'pending'")
        pending_revenue = cursor.fetchone()[0] or 0
        
        # User counts
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM payments WHERE status = 'verified'")
        total_customers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending_signups = cursor.fetchone()[0]
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error getting stats from database: {e}")
        # Fall back to JSON
        load()
        
        total = sum(p["amount"] for p in data["payments"])
        pro = sum(1 for p in data["payments"] if p["plan"] == "pro")
        business = sum(1 for p in data["payments"] if p["plan"] == "business")
        
        current_month = datetime.now().month
        monthly = sum(
            p["amount"] for p in data["payments"] 
            if datetime.fromisoformat(p["time"]).month == current_month
        )
        
        pending_revenue = sum(d["amount"] for d in data["pending"].values())
        total_customers = len(data["payments"])
        pending_signups = len(data["pending"])
    
    text = f"""📊 *{BOT_NAME} BUSINESS STATISTICS*

*Financial Performance:*
Total Revenue: {total:,} ETB
Current Month: {monthly:,} ETB
Pending Revenue: {pending_revenue:,} ETB
Average/Customer: {total/max(total_customers, 1):,.0f} ETB

*Customer Metrics:*
Total Customers: {total_customers}
PRO Customers: {pro}
BUSINESS Customers: {business}
Pending Signups: {pending_signups}

*Projections (Based on Current Rate):*
Daily: {(monthly/30):,.0f} ETB
Weekly: {(monthly/4.3):,.0f} ETB
Monthly: {monthly:,} ETB
Annual: {monthly*12:,} ETB

*Platform Health:*
🟢 Bot Status: ONLINE
🤖 Username: {BOT_USERNAME}
👑 Admin ID: {ADMIN_ID}
💾 Database: Active ✅

*Next Milestones:*
🎯 10 Customers: {1490 - total:,} ETB to go
🎯 50 Customers: {7450 - total:,} ETB to go
🎯 100 Customers: {14900 - total:,} ETB to go

*Keep growing! Every customer brings you closer to success!* 🚀"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# NEW DATABASE ADMIN COMMANDS
# ======================
async def db_info(update: Update, context):
    """Show database information"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    try:
        # Get database stats
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'verified'")
        payment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified'")
        total_revenue = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Get file info
        db_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
        backup_count = len(list_backups())
        
        text = f"""💾 *DATABASE INFORMATION*

*Database File:* `{DATABASE_PATH}`
*Size:* {db_size:,} bytes ({db_size/1024/1024:.1f} MB)
*Backups:* {backup_count} available

*Data Statistics:*
👥 Total Users: {user_count}
💰 Verified Payments: {payment_count}
⏳ Pending Payments: {pending_count}
💵 Total Revenue: {total_revenue:,} ETB

*Commands:*
`/backup` - Create database backup
`/restore` - Restore from backup
`/db_stats` - Detailed database stats

*Railway Persistence:* ✅ Active"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in db_info: {e}")
        await update.message.reply_text(f"❌ Error getting database info: {e}")

async def backup_cmd(update: Update, context):
    """Create database backup"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    success, result = create_backup()
    
    if success:
        file_size = os.path.getsize(result)
        
        # Send backup file to admin
        with open(result, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(result),
                caption=f"✅ *DATABASE BACKUP CREATED*\n\n"
                       f"📁 File: `{os.path.basename(result)}`\n"
                       f"📏 Size: {file_size:,} bytes\n"
                       f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                       f"*Save this file for emergency recovery!*",
                parse_mode='Markdown'
            )
        
        logger.info(f"📦 Backup created: {result}")
    else:
        await update.message.reply_text(f"❌ Backup failed: {result}")

async def list_backups_cmd(update: Update, context):
    """List available backups"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    backups = list_backups()
    
    if not backups:
        await update.message.reply_text("📭 No backups found.")
        return
    
    text = "📦 *AVAILABLE BACKUPS*\n\n"
    total_size = 0
    
    for i, backup in enumerate(backups[:5], 1):
        text += f"*{i}. {backup['name']}*\n"
        text += f"   Size: {backup['size']:,} bytes\n"
        text += f"   Date: {backup['modified'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        total_size += backup['size']
    
    if len(backups) > 5:
        text += f"... and {len(backups) - 5} more backups\n\n"
    
    text += f"*Total Backups:* {len(backups)}\n"
    text += f"*Total Size:* {total_size:,} bytes ({total_size/1024/1024:.1f} MB)\n\n"
    text += "*Restore with:* `/restore [filename]`"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def restore_cmd(update: Update, context):
    """Restore database from backup"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/restore [filename]`\n\n"
            "Example: `/restore backup_20240101_120000.db`\n\n"
            "Use `/list_backups` to see available backups."
        )
        return
    
    filename = context.args[0]
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        await update.message.reply_text(f"❌ Backup file not found: `{filename}`")
        return
    
    try:
        # Create backup of current database first
        current_backup = os.path.join(BACKUP_DIR, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, current_backup)
        
        # Restore from backup
        shutil.copy2(backup_path, DATABASE_PATH)
        
        text = f"""✅ *DATABASE RESTORED SUCCESSFULLY*

📁 Source: `{filename}`
📏 Size: {os.path.getsize(DATABASE_PATH):,} bytes
🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*Important:*
1. Current database backed up as: `{os.path.basename(current_backup)}`
2. Bot needs to be restarted for changes to take effect
3. Check data integrity with `/db_info`

*Warning:* This is a destructive operation!"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.warning(f"⚠️ Database restored from backup: {filename}")
        
    except Exception as e:
        error_msg = f"❌ Restore failed: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def db_stats_cmd(update: Update, context):
    """Detailed database statistics"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        text = "📊 *DETAILED DATABASE STATISTICS*\n\n"
        
        for table in tables:
            table_name = table['name']
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            row_count = cursor.fetchone()['count']
            
            text += f"*{table_name.upper()}*\n"
            text += f"  Rows: {row_count:,}\n"
            
            # Get column info for main tables
            if table_name in ['users', 'payments']:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                text += f"  Columns: {len(columns)}\n"
        
        # Get database file info
        db_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
        backup_count = len(list_backups())
        
        text += f"\n*Database File:*\n"
        text += f"  Path: `{DATABASE_PATH}`\n"
        text += f"  Size: {db_size:,} bytes\n"
        text += f"  Backups: {backup_count}\n"
        text += f"  Railway: {'✅ Active' if '/workspace' in os.getcwd() else '❌ Not on Railway'}"
        
        conn.close()
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in db_stats: {e}")
        await update.message.reply_text(f"❌ Error getting database stats: {e}")

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
    
    # Admin commands (existing)
    app.add_handler(CommandHandler("revenue", revenue))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("stats", stats))
    
    # Database admin commands (new)
    app.add_handler(CommandHandler("db_info", db_info))
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("list_backups", list_backups_cmd))
    app.add_handler(CommandHandler("restore", restore_cmd))
    app.add_handler(CommandHandler("db_stats", db_stats_cmd))
    
    # Button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("=" * 70)
    logger.info(f"🚀 {BOT_NAME} - PRODUCTION VERSION WITH DATABASE")
    logger.info(f"🌟 {BOT_SLOGAN}")
    logger.info(f"🤖 Bot: {BOT_USERNAME}")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"💾 Database: {DATABASE_PATH}")
    logger.info(f"📱 telebirr: {TELEBIRR}")
    logger.info(f"🏦 CBE: {CBE}")
    logger.info(f"📞 Support: {SUPPORT}")
    logger.info(f"💰 Payments: {PAYMENTS}")
    logger.info("✅ DATABASE SYSTEM INTEGRATED!")
    logger.info("✅ ALL SYSTEMS READY FOR REVENUE!")
    logger.info("=" * 70)
    
    app.run_polling()

if __name__ == "__main__":
    main()
