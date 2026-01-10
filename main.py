#!/usr/bin/env python3
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# Health check handler
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode())
    
    def log_message(self, format, *args):
        pass

def start_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"✅ Health server on port {PORT}")
    server.serve_forever()

# Bot command
async def start(update: Update, context):
    await update.message.reply_text("SHEGER ET Bot ✅")

def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN missing")
        return
    
    # Start health server
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Start bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    logger.info("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
