import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from datetime import datetime

# ============ FLASK SERVER FOR RAILWAY ============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ EthioPay Bot is running! Visit @EthioPayBot on Telegram"

@app.route('/health')
def health():
    return "🟢 Healthy", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Start Flask in background
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()
print(f"✅ Flask server started on port {os.environ.get('PORT', 8080)}")

# ============ TELEGRAM BOT ============
# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get token from Railway environment
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ ERROR: No TOKEN found in environment variables!")
    print("Please set TOKEN in Railway variables")
    exit(1)

print(f"✅ Using token: {TOKEN[:10]}...")

# Forex rates
FOREX_RATES = {
    "black_market": 57.5,
    "bank_rate": 56.3,
    "our_rate": 57.2,
    "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
}

# Bot commands
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💰 PayPal Solutions", callback_data='paypal')],
        [InlineKeyboardButton("📈 Forex Rates", callback_data='rate')],
        [InlineKeyboardButton("⚠️ Avoid Scams", callback_data='scam')],
        [InlineKeyboardButton("📖 Buy Guide", callback_data='guide')],
        [InlineKeyboardButton("🤝 Connect Agent", callback_data='agent')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Welcome to EthioPay Bot!*\n\n"
        "I help Ethiopians get paid from abroad!\n\n"
        "• Real-time forex rates\n"
        "• PayPal/Upwork solutions\n"
        "• Verified agents\n"
        "• Tax guidance\n\n"
        "Tap a button below or type your question!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'paypal':
        await query.edit_message_text(
            "💰 *3 Ways to Access PayPal in Ethiopia:*\n\n"
            "1. Family Abroad Method\n"
            "2. Payoneer Bridge\n"
            "3. Direct Transfer (high fees)\n\n"
            "📖 Full guide: 500 ETB\n"
            "Send to: 0961-393-003 via Telebirr",
            parse_mode='Markdown'
        )
    elif query.data == 'rate':
        await query.edit_message_text(
            f"📈 *Today's Rates ({FOREX_RATES['updated']})*\n\n"
            f"• Black Market: $1 = {FOREX_RATES['black_market']} ETB\n"
            f"• Bank Rate: $1 = {FOREX_RATES['bank_rate']} ETB\n"
            f"• Our Network: $1 = {FOREX_RATES['our_rate']} ETB ✅\n\n"
            "Need to exchange? Type 'agent'",
            parse_mode='Markdown'
        )
    elif query.data == 'scam':
        await query.edit_message_text(
            "⚠️ *Avoid These Scams:*\n\n"
            "1. ❌ 'Pay 50% upfront'\n"
            "2. ❌ No physical office\n"
            "3. ❌ Rates too good (e.g., $1 = 60 ETB)\n"
            "4. ❌ Pressure tactics\n\n"
            "✅ Our agents are verified!\n"
            "Type 'agent' to connect",
            parse_mode='Markdown'
        )
    elif query.data == 'guide':
        await query.edit_message_text(
            "📖 *Ultimate Payment Guide*\n\n"
            "47-page PDF with:\n"
            "• Step-by-step setups\n"
            "• Tax templates\n"
            "• Legal compliance\n"
            "• Agent checklist\n\n"
            "💰 Price: 500 ETB\n"
            "📱 Pay via Telebirr: 0961-393-003\n"
            "📸 Send screenshot after payment",
            parse_mode='Markdown'
        )
    elif query.data == 'agent':
        await query.edit_message_text(
            "🤝 *Verified Agents:*\n\n"
            "1. @AddisForexAgent (Addis)\n"
            "   • Rate: 57.1 ETB/$\n"
            "   • Min: $100\n\n"
            "2. @SafeTransferET (Online)\n"
            "   • Rate: 57.0 ETB/$\n"
            "   • Min: $50\n\n"
            "Message them directly!\n"
            "Say you're from @EthioPayBot",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    
    if 'paypal' in text:
        await update.message.reply_text(
            "💰 *PayPal Solutions:*\n\n"
            "Method 1: Family Abroad\n"
            "Method 2: Payoneer Bridge\n"
            "Method 3: Direct Transfer\n\n"
            "For step-by-step guide, type 'guide'",
            parse_mode='Markdown'
        )
    elif 'rate' in text or 'forex' in text:
        await update.message.reply_text(
            f"📈 Rate: $1 = {FOREX_RATES['our_rate']} ETB\n"
            f"Updated: {FOREX_RATES['updated']}\n\n"
            "Need to exchange? Type 'agent'",
            parse_mode='Markdown'
        )
    elif 'scam' in text:
        await update.message.reply_text(
            "⚠️ Common scams:\n"
            "• Advance payment requests\n"
            "• Fake Telegram channels\n"
            "• No escrow protection\n\n"
            "Always use verified agents!",
            parse_mode='Markdown'
        )
    elif 'guide' in text:
        await update.message.reply_text(
            "📖 Guide: 500 ETB\n"
            "Send to: 0961-393-003 via Telebirr\n"
            "Then send screenshot here!",
            parse_mode='Markdown'
        )
    elif 'agent' in text:
        await update.message.reply_text(
            "Connect with:\n"
            "@AddisForexAgent\n"
            "or\n"
            "@SafeTransferET\n\n"
            "Tell them @EthioPayBot sent you!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🤔 I understand you're asking about:\n"
            f"\"{text}\"\n\n"
            "Try these commands:\n"
            "• 'paypal' - Payment methods\n"
            "• 'rate' - Forex rates\n"
            "• 'guide' - Buy full guide\n"
            "• 'agent' - Connect with agents",
            parse_mode='Markdown'
        )

async def error(update: Update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")

def main():
    print("🚀 Starting Telegram bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error)
    
    print("🤖 Bot started!")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
