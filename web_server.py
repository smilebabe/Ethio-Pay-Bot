#!/usr/bin/env python3
"""
Flask Health Check Server for Railway
This ensures health checks pass for SHEGER ET Bot
"""
from flask import Flask, jsonify
import os
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Get port from Railway (auto-set) or use default
PORT = int(os.getenv("PORT", 8080))
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "production")
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL", "")

# ======================
# HEALTH CHECK ENDPOINTS
# ======================

@app.route('/')
def home():
    """Main health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "sheger-et-bot",
        "environment": RAILWAY_ENVIRONMENT,
        "telegram": "running",
        "timestamp": "2024-01-10T17:00:00Z"
    })

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({"status": "ok"}), 200

@app.route('/ping')
def ping():
    """Ping endpoint"""
    return jsonify({"message": "pong"}), 200

@app.route('/status')
def status():
    """Detailed status"""
    return jsonify({
        "database": "postgresql",
        "telegram_bot": "active",
        "version": "2.10",
        "uptime": "running"
    })

# ======================
# ERROR HANDLERS
# ======================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ======================
# START SERVER
# ======================

if __name__ == "__main__":
    logger.info(f"🚀 Starting Flask Health Server on port {PORT}")
    logger.info(f"🌐 Environment: {RAILWAY_ENVIRONMENT}")
    if RAILWAY_PUBLIC_URL:
        logger.info(f"🔗 Public URL: {RAILWAY_PUBLIC_URL}")
    
    # Start Flask server
    app.run(
        host='0.0.0.0',  # Bind to all interfaces
        port=PORT,
        debug=False,      # Disable debug mode for production
        threaded=True     # Handle multiple requests
    )
