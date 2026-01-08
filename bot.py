#!/usr/bin/env python3
"""
SHEGER ET V2 - Fixed Admin Commands
Complete working version with /verify and /pending commands
"""

import os
import json
import logging
import sqlite3
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ======================
# CONFIGURATION
# ======================
TELEBIRR = "0961393001"
CBE = "1000645865603"
ADMIN_ID = 7714584854  # Your admin ID

SUPPORT = "@ShegerESupport"
PAYMENTS = "@ShegerPayments"
SALES = "@ShegerESales"
NEWS = "@ShegeErNews"

BOT_NAME = "SHEGER ET"
BOT_SLOGAN = "Ethiopia's All-in-One Super App"

# ======================
# DATABASE SETUP
# ======================
DATABASE_PATH = "sheger_et.db"

def init_database():
    """Initialize database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Users table
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
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_payment TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Payments table
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
                expires_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("✅ Database initialized")
        return True
        
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {e}")
        return False

# Initialize database
init_database()

# ======================
# DATABASE FUNCTIONS
# ======================
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_or_update_user(user_id: int, username: str, full_name: str):
    """Create or update user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update
            cursor.execute('''
                UPDATE users 
                SET username = ?, full_name = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username, full_name, user_id))
        else:
            # Create new
            referral_code = generate_referral_code(user_id)
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, full_name, referral_code, joined_at, last_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, username, full_name, referral_code))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return False

def generate_referral_code(user_id: int) -> str:
    """Generate referral code"""
    prefix = "SHEGER"
    unique = f"{user_id:06d}"[-6:]
    chars = ''.join(random.choices(string.ascii_uppercase, k=4))
    return f"{prefix}{unique}{chars}"

def create_payment(user_id: int, username: str, plan: str, amount: float) -> str:
    """Create payment record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        reference_code = f"{plan.upper()}-{user_id}-{int(datetime.now().timestamp())}"
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO payments 
            (user_id, username, plan, amount, reference_code, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, plan, amount, reference_code, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Payment created: {user_id} - {plan} - {amount}")
        return reference_code
        
    except Exception as e:
        logging.error(f"Error creating payment: {e}")
        return None

def get_pending_payments() -> List[Dict]:
    """Get all pending payments"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, u.full_name, u.phone 
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
        ''')
        
        payments = cursor.fetchall()
        conn.close()
        
        result = []
        for payment in payments:
            result.append({
                'id': payment['id'],
                'user_id': payment['user_id'],
                'username': payment['username'],
                'full_name': payment['full_name'],
                'phone': payment['phone'],
                'plan': payment['plan'],
                'amount': payment['amount'],
                'reference_code': payment['reference_code'],
                'created_at': payment['created_at'],
                'expires_at': payment['expires_at']
            })
        
        return result
        
    except Exception as e:
        logging.error(f"Error getting pending payments: {e}")
        return []

def verify_payment(user_id: int, admin_id: int) -> tuple:
    """Verify a payment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest pending payment for user
        cursor.execute('''
            SELECT * FROM payments 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        
        payment = cursor.fetchone()
        if not payment:
            conn.close()
            return False, "No pending payment found"
        
        # Update payment
        cursor.execute('''
            UPDATE payments 
            SET status = 'verified', 
                verified_by = ?, 
                verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (admin_id, payment['id']))
        
        # Update user
        cursor.execute('''
            UPDATE users 
            SET plan = ?, 
                total_spent = total_spent + ?,
                last_payment = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (payment['plan'], payment['amount'], user_id))
        
        conn.commit()
        conn.close()
        
        return True, f"Payment verified! User {user_id} upgraded to {payment['plan'].upper()}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_user_balance(user_id: int) -> float:
    """Get user balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result['balance'] if result else 0.0
    except:
        return 0.0

def get_user_plan(user_id: int) -> str:
    """Get user plan"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT plan FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result['plan'] if result else 'basic'
    except:
        return 'basic'

# ======================
# ADMIN COMMANDS - FIXED
# ======================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin dashboard"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Get stats
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'verified'")
    verified_payments = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'verified'")
    total_revenue = cursor.fetchone()[0] or 0
    
    conn.close()
    
    text = f"""
👑 *SHEGER ET ADMIN DASHBOARD*

*Platform Stats:*
👥 Total Users: {total_users}
💰 Total Revenue: {total_revenue:,.0f} ETB
✅ Verified Payments: {verified_payments}
⏳ Pending Payments: {pending_payments}

*Admin Commands:*
`/verify USER_ID` - Verify payment
`/pending` - Show pending payments
`/users` - List all users
`/revenue` - Revenue report
`/broadcast MESSAGE` - Send announcement

*Quick Actions:*
1. Check pending payments
2. Verify user payments
3. Monitor platform activity
4. Send announcements
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify payment command - FIXED"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/verify USER_ID`\n\n"
            "Example: `/verify 123456789`\n"
            "Will verify the latest pending payment for this user.",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        # Verify payment
        success, message = verify_payment(user_id, ADMIN_ID)
        
        if success:
            # Get user info
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT username, plan FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            username = user['username'] if user else "Unknown"
            plan = user['plan'] if user else "basic"
            
            await update.message.reply_text(
                f"✅ *PAYMENT VERIFIED*\n\n"
                f"User: @{username}\n"
                f"User ID: `{user_id}`\n"
                f"Plan: {plan.upper()}\n"
                f"Verified by: Admin\n\n"
                f"User has been upgraded successfully!",
                parse_mode='Markdown'
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ *PAYMENT VERIFIED!*\n\n"
                         f"Your payment has been verified and your account has been upgraded to {plan.upper()}!\n"
                         f"Thank you for choosing {BOT_NAME}! 🎉\n\n"
                         f"Use /start to see your new features.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.warning(f"Could not notify user {user_id}: {e}")
                
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payments - FIXED"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Get pending payments
    pending_payments = get_pending_payments()
    
    if not pending_payments:
        await update.message.reply_text("✅ No pending payments.")
        return
    
    # Format message
    text = "⏳ *PENDING PAYMENTS*\n\n"
    
    for i, payment in enumerate(pending_payments, 1):
        created = datetime.fromisoformat(payment['created_at']).strftime("%b %d, %H:%M")
        expires = datetime.fromisoformat(payment['expires_at']).strftime("%b %d, %H:%M") if payment['expires_at'] else "N/A"
        
        text += f"""*{i}. @{payment['username'] or 'N/A'}*
👤 {payment['full_name'] or 'Unknown'}
📞 {payment['phone'] or 'N/A'}
🆔 ID: `{payment['user_id']}`
💎 Plan: {payment['plan'].upper()}
💰 Amount: {payment['amount']} ETB
📋 Ref: `{payment['reference_code']}`
📅 Created: {created}
⏰ Expires: {expires}

"""
    
    text += f"\nTotal: {len(pending_payments)} pending payments."
    text += "\n\nUse `/verify USER_ID` to verify a payment."
    
    # Send in chunks if too long
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, full_name, plan, balance, joined_at
        FROM users 
        ORDER BY joined_at DESC 
        LIMIT 50
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    text = "👥 *RECENT USERS*\n\n"
    
    for i, user in enumerate(users, 1):
        join_date = datetime.fromisoformat(user['joined_at']).strftime("%b %d")
        text += f"""*{i}. @{user['username'] or 'N/A'}*
👤 {user['full_name']}
🆔 `{user['user_id']}`
🏷️ {user['plan'].upper()}
💰 {user['balance']:,.0f} ETB
📅 {join_date}

"""
    
    text += f"\nTotal users: {len(users)} shown (most recent)"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def revenue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revenue report"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Today's revenue
    cursor.execute('''
        SELECT SUM(amount) as today_revenue 
        FROM payments 
        WHERE status = 'verified' 
        AND DATE(verified_at) = DATE('now')
    ''')
    today = cursor.fetchone()['today_revenue'] or 0
    
    # This week's revenue
    cursor.execute('''
        SELECT SUM(amount) as week_revenue 
        FROM payments 
        WHERE status = 'verified' 
        AND verified_at >= DATE('now', '-7 days')
    ''')
    week = cursor.fetchone()['week_revenue'] or 0
    
    # This month's revenue
    cursor.execute('''
        SELECT SUM(amount) as month_revenue 
        FROM payments 
        WHERE status = 'verified' 
        AND strftime('%Y-%m', verified_at) = strftime('%Y-%m', 'now')
    ''')
    month = cursor.fetchone()['month_revenue'] or 0
    
    # All time revenue
    cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "verified"')
    total = cursor.fetchone()[0] or 0
    
    # Revenue by plan
    cursor.execute('''
        SELECT plan, COUNT(*) as count, SUM(amount) as revenue
        FROM payments 
        WHERE status = 'verified'
        GROUP BY plan
        ORDER BY revenue DESC
    ''')
    plan_stats = cursor.fetchall()
    
    conn.close()
    
    text = f"""
💰 *REVENUE REPORT*

*Time Periods:*
📊 Today: {today:,.0f} ETB
📈 This Week: {week:,.0f} ETB
📅 This Month: {month:,.0f} ETB
🏆 All Time: {total:,.0f} ETB

*Revenue by Plan:*
"""
    
    for stat in plan_stats:
        text += f"• {stat['plan'].upper()}: {stat['revenue']:,.0f} ETB ({stat['count']} payments)\n"
    
    text += f"\n*Average per payment:* {(total/sum(stat['count'] for stat in plan_stats)) if plan_stats else 0:,.0f} ETB"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/broadcast Your message here`\n\n"
            "Example: `/broadcast New feature added! Check it out.`",
            parse_mode='Markdown'
        )
        return
    
    message = ' '.join(context.args)
    
    # Get all users
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status = 'active'")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    await update.message.reply_text(f"📢 Broadcasting to {total} users...")
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *ANNOUNCEMENT FROM {BOT_NAME}*\n\n{message}\n\n_This is an automated broadcast._",
                parse_mode='Markdown'
            )
            success += 1
            
            # Small delay to avoid rate limits
            if success % 20 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send to {user['user_id']}: {e}")
    
    # Send report
    await update.message.reply_text(
        f"📊 *BROADCAST COMPLETE*\n\n"
        f"✅ Successful: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📈 Success rate: {success/total*100:.1f}%",
        parse_mode='Markdown'
    )

# ======================
# USER COMMANDS
# ======================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    # Create/update user
    create_or_update_user(user.id, user.username, user.full_name)
    
    # Get user info
    balance = get_user_balance(user.id)
    plan = get_user_plan(user.id)
    
    keyboard = [
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet"),
         InlineKeyboardButton("💸 Send Money", callback_data="send")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit"),
         InlineKeyboardButton("📤 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏪 Marketplace", callback_data="marketplace"),
         InlineKeyboardButton("🔧 Services", callback_data="services")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📞 Support", url=f"https://t.me/{SUPPORT.replace('@', '')}")]
    ]
    
    text = f"""
🏙️ *{BOT_NAME}* 🇪🇹
*{BOT_SLOGAN}*

Welcome, *{user.full_name}*!

💰 *Balance:* {balance:,.2f} ETB
🏷️ *Plan:* {plan.upper()}
🌟 *Status:* Active ✅

*Quick Actions:*
• Check your wallet balance
• Send money to friends
• Deposit via TeleBirr or bank
• Browse marketplace
• Access various services

*Need help?* Tap Support below.
"""
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wallet command"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = get_user_balance(user_id)
    plan = get_user_plan(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💸 Quick Send", callback_data="quick_send"),
         InlineKeyboardButton("📥 Deposit Now", callback_data="deposit_now")],
        [InlineKeyboardButton("📋 History", callback_data="history"),
         InlineKeyboardButton("💳 Cards", callback_data="cards")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    
    text = f"""
💰 *Your SHEGER Wallet*

*Available Balance:* {balance:,.2f} ETB
*Plan:* {plan.upper()}
*Status:* Active ✅

*Quick Actions:*
• Send money instantly
• Add funds to wallet
• View transaction history
• Manage payment methods

*Ready to transact?*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deposit command"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    keyboard = [
        [InlineKeyboardButton("📱 TeleBirr", callback_data="deposit_telebirr"),
         InlineKeyboardButton("🏦 Bank Transfer", callback_data="deposit_bank")],
        [InlineKeyboardButton("💵 Cash Agent", callback_data="deposit_agent"),
         InlineKeyboardButton("🔙 Back", callback_data="back_wallet")]
    ]
    
    text = f"""
📥 *Deposit Money*

*Choose method:*
1. 📱 *TeleBirr* - Instant, 0% fee
2. 🏦 *Bank Transfer* - CBE & other banks
3. 💵 *Cash Agent* - Deposit at agent

*Instructions will be provided after selection.*

*Minimum:* 10 ETB
*Maximum:* 50,000 ETB

*Select your preferred method:*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deposit_telebirr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TeleBirr deposit"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 *TeleBirr Deposit*\n\n"
        "Please send the amount you want to deposit (in ETB):\n\n"
        "*Example:* `1000`\n\n"
        "Minimum: 10 ETB\n"
        "Maximum: 50,000 ETB\n"
        "Fee: 0%\n\n"
        "Enter amount now:",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_deposit'] = {
        'method': 'telebirr',
        'step': 'amount'
    }

# ======================
# BUTTON HANDLER
# ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "wallet":
        await wallet_command(update, context)
    elif data == "deposit":
        await deposit_command(update, context)
    elif data == "deposit_telebirr":
        await deposit_telebirr_handler(update, context)
    elif data == "back":
        await start_command(update, context)
    elif data == "back_wallet":
        await wallet_command(update, context)

# ======================
# MESSAGE HANDLER
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user = update.effective_user
    text = update.message.text
    
    # Check if awaiting deposit amount
    if context.user_data.get('awaiting_deposit') and context.user_data['awaiting_deposit'].get('step') == 'amount':
        try:
            amount = float(text)
            
            if amount < 10:
                await update.message.reply_text("❌ Minimum deposit is 10 ETB.")
                return
            
            if amount > 50000:
                await update.message.reply_text("❌ Maximum deposit is 50,000 ETB.")
                return
            
            method = context.user_data['awaiting_deposit']['method']
            
            # Create payment record
            reference = create_payment(user.id, user.username, "pro", amount)
            
            if method == 'telebirr':
                await update.message.reply_text(
                    f"""
✅ *Deposit Request Created*

Amount: {amount:,.2f} ETB
Method: TeleBirr
Reference: `{reference}`
Status: Pending

*Instructions:*
1. Open TeleBirr app
2. Send to: `{TELEBIRR}`
3. Amount: {amount:,.2f} ETB
4. Reference: `{reference}`
5. Send payment proof to @{PAYMENTS}

*Admin will verify within 24 hours.*
                    """,
                    parse_mode='Markdown'
                )
            
            # Clear state
            context.user_data['awaiting_deposit'] = None
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")

# ======================
# MAIN FUNCTION
# ======================
def main():
    """Main function"""
    # Get token from environment or hardcode
    TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        logging.error("❌ Please set your Telegram bot token!")
        logging.info("💡 Edit the TOKEN variable or set TELEGRAM_TOKEN environment variable")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("revenue", revenue_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    logging.info(f"🤖 {BOT_NAME} is starting...")
    application.run_polling()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    main()
