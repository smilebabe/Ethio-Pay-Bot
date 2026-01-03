import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from Railway
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ ERROR: No TOKEN found in Railway variables!")
    print("Please set TOKEN in Railway → Variables")
    exit(1)

print(f"✅ Bot starting with token: {TOKEN[:15]}...")

# Forex rates
FOREX_RATES = {
    "black_market": 57.5,
    "bank_rate": 56.3,
    "our_rate": 57.2,
    "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
}

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💰 PayPal Solutions", callback_data='paypal')],
        [InlineKeyboardButton("📈 Forex Rates", callback_data='rate')],
        [InlineKeyboardButton("⚠️ Avoid Scams", callback_data='scam')],
        [InlineKeyboardButton("📖 Buy Guide (500 ETB)", callback_data='guide')],
        [InlineKeyboardButton("🤝 Connect Agent", callback_data='agent')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Welcome to EthioPay Bot!*\n\n"
        "*I solve Ethiopian payment problems:*\n"
        "• Receive PayPal/Upwork money\n"
        "• Best forex rates\n"
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
        response = """💰 *3 Ways to Access PayPal in Ethiopia:*

1️⃣ *Family Abroad Method*
   • Relative receives PayPal
   • Transfers to their bank
   • Sends you via Telebirr
   📊 *Fees:* 2-5%

2️⃣ *Payoneer Bridge*
   • Create Payoneer account
   • Receive to Payoneer
   • Withdraw to Ethiopian bank
   📊 *Fees:* 1.8-2.5%

3️⃣ *Direct Bank Transfer* (Not recommended)
   • Bank converts at official rate
   • You lose 15-25%
   📊 *Fees:* 20-30%

📖 *Full step-by-step guide:* /guide"""
        
    elif query.data == 'rate':
        response = f"""📈 *Today's Forex Rates ({FOREX_RATES['updated']})*

• *Black Market:* $1 = {FOREX_RATES['black_market']} ETB
• *Bank Rate:* $1 = {FOREX_RATES['bank_rate']} ETB
• *Our Network:* $1 = {FOREX_RATES['our_rate']} ETB ✅

*Need to exchange?* Type 'agent' or /agent"""
        
    elif query.data == 'scam':
        response = """⚠️ *10 Forex Scams to Avoid:*

1. "Pay 50% upfront" ❌
2. No physical office ❌
3. Fake Telegram channels ❌
4. Rates too good (e.g., $1 = 60 ETB) ❌
5. Pressure tactics ("last chance") ❌
6. No client testimonials ❌
7. Asking for ID photos early ❌
8. Western Union only ❌
9. No escrow system ❌
10. Unregistered businesses ❌

✅ *Our Verified Agents:* /agent"""
        
    elif query.data == 'guide':
        response = """📖 *EthiPay Ultimate Guide* - 500 ETB

*What's inside:*
✅ 47-page PDF with screenshots
✅ Step-by-step payment setups
✅ Tax calculation templates
✅ Legal compliance checklist
✅ Agent verification checklist
✅ Sample client contracts

*How to get it:*
1. Send 500 ETB via Telebirr to *0961-393-003*
2. Send payment screenshot here
3. Receive guide within 5 minutes

💰 *Bonus:* First 100 buyers get free consultation!"""
        
    elif query.data == 'agent':
        response = """🤝 *Verified Forex Agents*

1️⃣ *Addis Forex Solutions* (Addis)
   • Rate: $1 = 57.1 ETB
   • Min: $100
   • Commission: 9%
   • Contact: @AddisForexAgent

2️⃣ *Safe Transfer Ethiopia* (Online)
   • Rate: $1 = 57.0 ETB
   • Min: $50
   • Commission: 8.5%
   • Contact: @SafeTransferET

3️⃣ *Diaspora Bridge* (US/Canada focus)
   • Rate: $1 = 57.3 ETB
   • Min: $200
   • Commission: 10%
   • Contact: @DiasporaBridge

⚠️ *Always ask for escrow!* Never pay 100% upfront.

*Need help choosing?* Describe:
• Amount: ______ USD
• Location: ______
• Urgency: ______"""
    
    await query.edit_message_text(response, parse_mode='Markdown')

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    
    # Keyword matching
    if any(word in text for word in ['paypal', 'pay pal', 'stripe', 'wise']):
        response = """💸 *PayPal Solutions:*
        
1. Family abroad method
2. Payoneer bridge
3. Direct transfer (not recommended)

For detailed guide: /guide"""
        
    elif any(word in text for word in ['rate', 'forex', 'birr', 'dollar', 'exchange']):
        response = f"💰 *Today's Rate:* $1 = {FOREX_RATES['our_rate']} ETB\nUpdated: {FOREX_RATES['updated']}\n\nNeed to exchange? /agent"
        
    elif any(word in text for word in ['scam', 'fake', 'fraud', 'trust', 'safe']):
        response = "⚠️ *Avoid scams:* Never pay 100% upfront, verify office address, check testimonials.\n\nSafe agents: /agent"
        
    elif any(word in text for word in ['guide', 'book', 'pdf', 'tutorial']):
        response = "📖 *Guide:* 500 ETB\nSend to: 0912-345-6789 via Telebirr\nThen send screenshot here!"
        
    elif any(word in text for word in ['agent', 'broker', 'exchange', 'change money']):
        response = "🤝 Connect with verified agents:\n@AddisForexAgent\n@SafeTransferET\n\nSay @EthiPayBot sent you!"
        
    elif any(word in text for word in ['hello', 'hi', 'hey', 'start']):
        response = "👋 Hello! I help Ethiopians get paid from abroad. Use /start for menu or ask about PayPal, rates, or agents."
        
    else:
        response = f"🤔 *I understand you're asking about:* \"{text}\"\n\n*Try these:*\n• 'paypal' - Payment methods\n• 'rate' - Forex rates\n• 'guide' - Buy guide\n• 'agent' - Connect agents\n\nOr use /start for menu"
    
    # Add footer
    footer = "\n\n📢 *Join:* @EthioPayments\n💎 *Premium:* /join"
    
    await update.message.reply_text(response + footer, parse_mode='Markdown')

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "ℹ️ *Available Commands:*\n\n"
        "/start - Main menu\n"
        "/rates - Current forex rates\n"
        "/guide - Buy payment guide (500 ETB)\n"
        "/agent - Connect with agents\n"
        "/join - Premium group (2000 ETB/month)\n\n"
        "*Or just type your question!*",
        parse_mode='Markdown'
    )

async def rates_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        f"📊 *Rates ({FOREX_RATES['updated']}):*\n\n"
        f"• Black Market: {FOREX_RATES['black_market']} ETB\n"
        f"• Bank Rate: {FOREX_RATES['bank_rate']} ETB\n"
        f"• Our Rate: {FOREX_RATES['our_rate']} ETB ✅",
        parse_mode='Markdown'
    )

def main():
    print("🚀 Starting EthioPay Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rates", rates_command))
    application.add_handler(CommandHandler("guide", lambda u, c: u.message.reply_text("Guide: 500 ETB\nSend to: 0912-345-6789")))
    application.add_handler(CommandHandler("agent", lambda u, c: u.message.reply_text("Agents:\n@AddisForexAgent\n@SafeTransferET")))
    application.add_handler(CommandHandler("join", lambda u, c: u.message.reply_text("Premium: 2000 ETB/month\nBenefits: Daily alerts, priority support")))
    
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot setup complete!")
    print("🤖 Starting polling...")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()
