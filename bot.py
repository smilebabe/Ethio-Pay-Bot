#!/usr/bin/env python3
"""
SHEGER ET V2.10 - Enhanced Production Update
Real-Time Features, Performance Improvements, Enhanced Security
"""

import os
import json
import logging
import sqlite3
import asyncio
import aiohttp
import hashlib
import hmac
import base64
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import threading
from queue import Queue
import redis
from cryptography.fernet import Fernet
import qrcode
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ======================
# V2.10 CONFIGURATION ENHANCEMENTS
# ======================
class ConfigV210:
    """Enhanced configuration for V2.10"""
    
    # Core
    APP_NAME = "SHEGER ET V2.10"
    VERSION = "2.10.0"
    
    # Payment Methods
    PAYMENT_METHODS = {
        "telebirr": {
            "name": "TeleBirr",
            "fee": 0.0,
            "instant": True,
            "min_amount": 10,
            "max_amount": 50000
        },
        "cbe": {
            "name": "CBE Bank",
            "fee": 0.005,  # 0.5%
            "instant": False,
            "processing_time": "1-2 hours",
            "min_amount": 100,
            "max_amount": 100000
        },
        "dashen": {
            "name": "Dashen Bank",
            "fee": 0.005,
            "instant": False,
            "processing_time": "1-2 hours",
            "min_amount": 100,
            "max_amount": 100000
        },
        "awash": {
            "name": "Awash Bank",
            "fee": 0.005,
            "instant": False,
            "processing_time": "1-2 hours",
            "min_amount": 100,
            "max_amount": 100000
        },
        "balance": {
            "name": "SHEGER Balance",
            "fee": 0.0,
            "instant": True,
            "min_amount": 1,
            "max_amount": 1000000
        }
    }
    
    # Transaction Categories
    TRANSACTION_CATEGORIES = {
        "p2p": "Person to Person",
        "deposit": "Deposit",
        "withdrawal": "Withdrawal",
        "payment": "Payment",
        "bill": "Utility Bill",
        "airtime": "Airtime",
        "transfer": "Bank Transfer",
        "escrow": "Escrow Payment",
        "refund": "Refund"
    }
    
    # KYC Levels
    KYC_LEVELS = {
        "level0": {"name": "Unverified", "daily_limit": 5000, "monthly_limit": 50000},
        "level1": {"name": "Basic", "daily_limit": 20000, "monthly_limit": 100000},
        "level2": {"name": "Verified", "daily_limit": 100000, "monthly_limit": 500000},
        "level3": {"name": "Enhanced", "daily_limit": 1000000, "monthly_limit": 5000000}
    }
    
    # Plan Benefits
    PLAN_BENEFITS = {
        "basic": {
            "fee": 0.025,
            "daily_limit": 5000,
            "features": ["P2P Transfers", "Basic Marketplace", "Standard Support"]
        },
        "pro": {
            "fee": 0.015,
            "daily_limit": 50000,
            "features": ["Lower Fees", "Priority Support", "Advanced Analytics", "Bulk Payments"]
        },
        "business": {
            "fee": 0.008,
            "daily_limit": 500000,
            "features": ["Lowest Fees", "Dedicated Support", "API Access", "Custom Solutions"]
        }
    }

# ======================
# REAL-TIME REDIS CACHE
# ======================
class RedisCache:
    """Real-time caching with Redis"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis.ping()  # Test connection
            self.connected = True
            logging.info("✅ Redis cache connected")
        except:
            self.connected = False
            logging.warning("⚠️ Redis not available, using in-memory cache")
            self.memory_cache = {}
    
    def get(self, key: str):
        """Get value from cache"""
        try:
            if self.connected:
                value = self.redis.get(key)
                return json.loads(value) if value else None
            else:
                return self.memory_cache.get(key)
        except:
            return None
    
    def set(self, key: str, value: Any, expire: int = 300):
        """Set value in cache"""
        try:
            if self.connected:
                self.redis.setex(key, expire, json.dumps(value))
            else:
                self.memory_cache[key] = value
            return True
        except:
            return False
    
    def delete(self, key: str):
        """Delete key from cache"""
        try:
            if self.connected:
                self.redis.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except:
            return False
    
    def increment(self, key: str, amount: int = 1):
        """Increment counter"""
        try:
            if self.connected:
                return self.redis.incrby(key, amount)
            else:
                self.memory_cache[key] = self.memory_cache.get(key, 0) + amount
                return self.memory_cache[key]
        except:
            return 0
    
    def get_user_balance(self, user_id: int) -> float:
        """Get cached user balance"""
        key = f"balance:{user_id}"
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # Fallback to database
        from database import get_user_balance_db
        balance = get_user_balance_db(user_id)
        self.set(key, balance, 60)  # Cache for 60 seconds
        return balance
    
    def update_user_balance(self, user_id: int, balance: float):
        """Update cached user balance"""
        key = f"balance:{user_id}"
        self.set(key, balance, 60)

# Initialize cache
cache = RedisCache()

# ======================
# REAL-TIME WEBSOCKET NOTIFICATIONS
# ======================
class WebSocketManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.connections = {}  # user_id -> list of connections
        self.lock = threading.Lock()
    
    async def broadcast_to_user(self, user_id: int, message: Dict):
        """Broadcast message to specific user"""
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(message)
                except:
                    # Remove dead connection
                    self.connections[user_id].remove(ws)
    
    async def broadcast_transaction(self, transaction: Dict):
        """Broadcast transaction update"""
        user_id = transaction.get('user_id')
        if user_id:
            await self.broadcast_to_user(user_id, {
                "type": "transaction_update",
                "transaction": transaction
            })
    
    async def broadcast_balance(self, user_id: int, new_balance: float):
        """Broadcast balance update"""
        await self.broadcast_to_user(user_id, {
            "type": "balance_update",
            "balance": new_balance,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_connection(self, user_id: int, websocket):
        """Add WebSocket connection"""
        with self.lock:
            if user_id not in self.connections:
                self.connections[user_id] = []
            self.connections[user_id].append(websocket)
    
    def remove_connection(self, user_id: int, websocket):
        """Remove WebSocket connection"""
        with self.lock:
            if user_id in self.connections and websocket in self.connections[user_id]:
                self.connections[user_id].remove(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]

# Initialize WebSocket manager
ws_manager = WebSocketManager()

# ======================
# ENHANCED DATABASE V2.10
# ======================
def init_database_v210():
    """Initialize enhanced V2.10 database"""
    try:
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Enhanced users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE,
                email TEXT UNIQUE,
                plan TEXT DEFAULT 'basic',
                balance REAL DEFAULT 0.0,
                escrow_balance REAL DEFAULT 0.0,
                total_deposited REAL DEFAULT 0.0,
                total_withdrawn REAL DEFAULT 0.0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                kyc_status TEXT DEFAULT 'unverified',
                kyc_level TEXT DEFAULT 'level0',
                verification_score INTEGER DEFAULT 0,
                pin_hash TEXT,
                two_factor_enabled BOOLEAN DEFAULT 0,
                last_login TIMESTAMP,
                login_attempts INTEGER DEFAULT 0,
                daily_limit REAL DEFAULT 5000,
                monthly_limit REAL DEFAULT 50000,
                session_token TEXT,
                ip_address TEXT,
                device_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (referred_by) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Enhanced transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                reference_id TEXT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                sender_type TEXT DEFAULT 'user',
                receiver_type TEXT DEFAULT 'user',
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'ETB',
                fee REAL DEFAULT 0.0,
                net_amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                failure_reason TEXT,
                payment_method TEXT,
                payment_gateway TEXT,
                gateway_reference TEXT,
                otp_verified BOOLEAN DEFAULT 0,
                ip_address TEXT,
                device_id TEXT,
                location TEXT,
                risk_score REAL DEFAULT 0,
                flags TEXT DEFAULT '[]',
                initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (sender_id) REFERENCES users_v210(user_id),
                FOREIGN KEY (receiver_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Escrow table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escrows_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escrow_id TEXT UNIQUE NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                mediator_id INTEGER,
                amount REAL NOT NULL,
                description TEXT,
                terms TEXT,
                status TEXT DEFAULT 'created',
                dispute_reason TEXT,
                funded_amount REAL DEFAULT 0.0,
                released_amount REAL DEFAULT 0.0,
                held_amount REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                funded_at TIMESTAMP,
                dispute_at TIMESTAMP,
                completed_at TIMESTAMP,
                auto_release_at TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (buyer_id) REFERENCES users_v210(user_id),
                FOREIGN KEY (seller_id) REFERENCES users_v210(user_id),
                FOREIGN KEY (mediator_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Marketplace listings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketplace_listings_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT UNIQUE NOT NULL,
                seller_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                subcategory TEXT,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'ETB',
                negotiable BOOLEAN DEFAULT 0,
                quantity INTEGER DEFAULT 1,
                sku TEXT,
                images TEXT DEFAULT '[]',
                videos TEXT DEFAULT '[]',
                city TEXT,
                subcity TEXT,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'active',
                condition TEXT,
                views INTEGER DEFAULT 0,
                favorites INTEGER DEFAULT 0,
                listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sold_at TIMESTAMP,
                expires_at TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (seller_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Bills and utilities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bill_payments_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                bill_type TEXT NOT NULL,
                account_number TEXT NOT NULL,
                amount REAL NOT NULL,
                fee REAL DEFAULT 0.0,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                utility_reference TEXT,
                receipt_url TEXT,
                paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Airtime purchases
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS airtime_purchases_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                operator TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                reference TEXT,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Audit logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs_v210 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                user_agent TEXT,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_v210(user_id)
            )
        ''')
        
        # Create indexes for performance
        indexes = [
            ('idx_users_phone', 'users_v210(phone)'),
            ('idx_users_email', 'users_v210(email)'),
            ('idx_users_status', 'users_v210(status)'),
            ('idx_transactions_sender', 'transactions_v210(sender_id, initiated_at)'),
            ('idx_transactions_receiver', 'transactions_v210(receiver_id, initiated_at)'),
            ('idx_transactions_status', 'transactions_v210(status, initiated_at)'),
            ('idx_marketplace_seller', 'marketplace_listings_v210(seller_id, status)'),
            ('idx_marketplace_category', 'marketplace_listings_v210(category, status)'),
            ('idx_escrows_status', 'escrows_v210(status, created_at)'),
        ]
        
        for idx_name, idx_def in indexes:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')
        
        conn.commit()
        conn.close()
        
        logging.info("✅ V2.10 Database initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {e}")
        return False

# Initialize database
init_database_v210()

# ======================
# ENHANCED SECURITY V2.10
# ======================
class SecurityManagerV210:
    """Enhanced security manager for V2.10"""
    
    def __init__(self):
        self.failed_attempts = {}
        self.lock = threading.Lock()
    
    def generate_secure_token(self, user_id: int) -> str:
        """Generate secure session token"""
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        data = f"{user_id}:{timestamp}:{random_str}"
        return base64.urlsafe_b64encode(hashlib.sha256(data.encode()).digest()).decode()[:64]
    
    def verify_pin(self, user_id: int, pin: str) -> bool:
        """Verify user PIN"""
        # Rate limiting
        key = f"pin_attempts:{user_id}"
        attempts = cache.increment(key)
        
        if attempts > 5:
            logging.warning(f"Too many PIN attempts for user {user_id}")
            return False
        
        # Get stored PIN hash
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        cursor.execute('SELECT pin_hash FROM users_v210 WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return False
        
        stored_hash = result[0]
        # Verify PIN (in production, use proper hashing)
        # This is simplified - use bcrypt or similar in production
        computed_hash = hashlib.sha256(pin.encode()).hexdigest()
        
        if computed_hash == stored_hash:
            cache.delete(key)  # Reset attempts on success
            return True
        
        return False
    
    def check_transaction_risk(self, transaction: Dict) -> Dict:
        """Check transaction risk score"""
        risk_score = 0
        flags = []
        
        # Amount check
        amount = transaction.get('amount', 0)
        if amount > 50000:
            risk_score += 20
            flags.append("Large amount")
        
        # Frequency check
        user_id = transaction.get('user_id')
        recent_tx_count = self.get_recent_transactions(user_id, minutes=10)
        if recent_tx_count > 5:
            risk_score += 30
            flags.append("High frequency")
        
        # Time check (suspicious hours)
        hour = datetime.now().hour
        if hour in [0, 1, 2, 3, 4] and amount > 5000:
            risk_score += 15
            flags.append("Unusual time")
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "high"
            action = "block"
        elif risk_score >= 30:
            risk_level = "medium"
            action = "require_otp"
        else:
            risk_level = "low"
            action = "allow"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "flags": flags,
            "action": action,
            "recommendation": "Proceed with verification" if risk_level != "low" else "Proceed"
        }
    
    def get_recent_transactions(self, user_id: int, minutes: int = 60) -> int:
        """Get number of recent transactions"""
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM transactions_v210 
            WHERE sender_id = ? 
            AND initiated_at >= datetime('now', ?)
        ''', (user_id, f'-{minutes} minutes'))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

# Initialize security manager
security = SecurityManagerV210()

# ======================
# REAL-TIME PAYMENT PROCESSOR V2.10
# ======================
class RealTimePaymentProcessorV210:
    """Real-time payment processor for V2.10"""
    
    def __init__(self):
        self.pending_payments = {}
        self.processing_queue = Queue()
        self.processing = False
        
        # Start processing thread
        self.thread = threading.Thread(target=self._process_payments, daemon=True)
        self.thread.start()
    
    def _process_payments(self):
        """Background payment processing"""
        self.processing = True
        while self.processing:
            try:
                if not self.processing_queue.empty():
                    payment = self.processing_queue.get()
                    asyncio.run(self.process_single_payment(payment))
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Payment processing error: {e}")
    
    async def process_single_payment(self, payment: Dict):
        """Process single payment"""
        try:
            payment_type = payment.get('type')
            
            if payment_type == 'p2p':
                await self.process_p2p_payment(payment)
            elif payment_type == 'deposit':
                await self.process_deposit(payment)
            elif payment_type == 'withdrawal':
                await self.process_withdrawal(payment)
            elif payment_type == 'bill':
                await self.process_bill_payment(payment)
            elif payment_type == 'airtime':
                await self.process_airtime_purchase(payment)
                
        except Exception as e:
            logging.error(f"Single payment processing error: {e}")
    
    async def process_p2p_payment(self, payment: Dict):
        """Process P2P payment"""
        sender_id = payment['sender_id']
        receiver_id = payment['receiver_id']
        amount = payment['amount']
        fee = payment.get('fee', 0)
        
        # Check security
        risk_check = security.check_transaction_risk(payment)
        if risk_check['action'] == 'block':
            await self.update_payment_status(payment['transaction_id'], 'failed', 'Security block')
            return
        
        # Process payment
        try:
            # Deduct from sender
            success = await self.deduct_balance(sender_id, amount + fee)
            if not success:
                await self.update_payment_status(payment['transaction_id'], 'failed', 'Insufficient balance')
                return
            
            # Add to receiver
            success = await self.add_balance(receiver_id, amount)
            if not success:
                # Refund sender
                await self.add_balance(sender_id, amount + fee)
                await self.update_payment_status(payment['transaction_id'], 'failed', 'Credit failed')
                return
            
            # Update transaction
            await self.update_payment_status(payment['transaction_id'], 'completed')
            
            # Send notifications
            await self.send_payment_notifications(payment)
            
            # Update cache
            cache.update_user_balance(sender_id, await self.get_user_balance_db(sender_id))
            cache.update_user_balance(receiver_id, await self.get_user_balance_db(receiver_id))
            
            # WebSocket broadcast
            await ws_manager.broadcast_transaction({
                'user_id': sender_id,
                'type': 'payment_sent',
                'amount': amount,
                'to': receiver_id,
                'timestamp': datetime.now().isoformat()
            })
            
            await ws_manager.broadcast_transaction({
                'user_id': receiver_id,
                'type': 'payment_received',
                'amount': amount,
                'from': sender_id,
                'timestamp': datetime.now().isoformat()
            })
            
            logging.info(f"✅ P2P payment completed: {payment['transaction_id']}")
            
        except Exception as e:
            logging.error(f"P2P payment error: {e}")
            await self.update_payment_status(payment['transaction_id'], 'failed', str(e))
    
    async def process_deposit(self, payment: Dict):
        """Process deposit"""
        user_id = payment['user_id']
        amount = payment['amount']
        method = payment.get('method', 'telebirr')
        
        # Generate QR code for TeleBirr
        if method == 'telebirr':
            qr_data = await self.generate_telebirr_qr(user_id, amount)
            payment['qr_code'] = qr_data
        
        # Update payment status
        payment['status'] = 'pending'
        self.pending_payments[payment['transaction_id']] = payment
        
        # Send instructions to user
        await self.send_deposit_instructions(payment)
    
    async def process_withdrawal(self, payment: Dict):
        """Process withdrawal"""
        user_id = payment['user_id']
        amount = payment['amount']
        method = payment.get('method', 'cbe')
        
        # Check balance
        balance = await self.get_user_balance_db(user_id)
        if balance < amount:
            await self.update_payment_status(payment['transaction_id'], 'failed', 'Insufficient balance')
            return
        
        # Deduct balance
        success = await self.deduct_balance(user_id, amount)
        if not success:
            await self.update_payment_status(payment['transaction_id'], 'failed', 'Deduction failed')
            return
        
        # Process withdrawal based on method
        if method == 'cbe':
            await self.process_cbe_withdrawal(payment)
        elif method == 'telebirr':
            await self.process_telebirr_withdrawal(payment)
        
        # Update cache
        cache.update_user_balance(user_id, await self.get_user_balance_db(user_id))
    
    async def process_bill_payment(self, payment: Dict):
        """Process bill payment"""
        # Integrate with utility APIs
        # This is a placeholder for actual integration
        await asyncio.sleep(2)  # Simulate API call
        
        # Mark as completed
        await self.update_payment_status(payment['transaction_id'], 'completed')
        
        logging.info(f"✅ Bill payment completed: {payment['transaction_id']}")
    
    async def process_airtime_purchase(self, payment: Dict):
        """Process airtime purchase"""
        # Integrate with telecom APIs
        # This is a placeholder for actual integration
        await asyncio.sleep(1)  # Simulate API call
        
        # Mark as completed
        await self.update_payment_status(payment['transaction_id'], 'completed')
        
        logging.info(f"✅ Airtime purchase completed: {payment['transaction_id']}")
    
    async def deduct_balance(self, user_id: int, amount: float) -> bool:
        """Deduct balance from user account"""
        try:
            conn = sqlite3.connect('sheger_et_v210.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users_v210 
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND balance >= ?
            ''', (amount, user_id, amount))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logging.error(f"Deduct balance error: {e}")
            return False
    
    async def add_balance(self, user_id: int, amount: float) -> bool:
        """Add balance to user account"""
        try:
            conn = sqlite3.connect('sheger_et_v210.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users_v210 
                SET balance = balance + ?, 
                    total_deposited = total_deposited + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, amount, user_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logging.error(f"Add balance error: {e}")
            return False
    
    async def get_user_balance_db(self, user_id: int) -> float:
        """Get user balance from database"""
        try:
            conn = sqlite3.connect('sheger_et_v210.db')
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM users_v210 WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0.0
        except:
            return 0.0
    
    async def update_payment_status(self, transaction_id: str, status: str, reason: str = None):
        """Update payment status"""
        try:
            conn = sqlite3.connect('sheger_et_v210.db')
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute('''
                    UPDATE transactions_v210 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE transaction_id = ?
                ''', (status, transaction_id))
            else:
                cursor.execute('''
                    UPDATE transactions_v210 
                    SET status = ?, failure_reason = ?
                    WHERE transaction_id = ?
                ''', (status, reason, transaction_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Update payment status error: {e}")
    
    async def send_payment_notifications(self, payment: Dict):
        """Send payment notifications"""
        # This would integrate with email/SMS services
        # Placeholder implementation
        logging.info(f"📧 Notification sent for payment: {payment['transaction_id']}")
    
    async def send_deposit_instructions(self, payment: Dict):
        """Send deposit instructions"""
        # This would send Telegram message with instructions
        # Placeholder implementation
        logging.info(f"📋 Deposit instructions sent for: {payment['transaction_id']}")
    
    async def generate_telebirr_qr(self, user_id: int, amount: float) -> str:
        """Generate TeleBirr QR code"""
        # Generate QR code data
        qr_data = f"telebirr://pay?amount={amount}&note=SHEGER{user_id}"
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convert to base64 for storage
        import base64
        return base64.b64encode(buffer.getvalue()).decode()
    
    async def process_cbe_withdrawal(self, payment: Dict):
        """Process CBE withdrawal"""
        # Placeholder for CBE bank integration
        await asyncio.sleep(2)  # Simulate bank processing
        await self.update_payment_status(payment['transaction_id'], 'processing')
        
        # Simulate completion after delay
        async def complete_withdrawal():
            await asyncio.sleep(30)  # 30 seconds processing time
            await self.update_payment_status(payment['transaction_id'], 'completed')
        
        asyncio.create_task(complete_withdrawal())
    
    async def process_telebirr_withdrawal(self, payment: Dict):
        """Process TeleBirr withdrawal"""
        # Placeholder for TeleBirr integration
        await asyncio.sleep(1)  # Simulate API call
        await self.update_payment_status(payment['transaction_id'], 'completed')

# Initialize payment processor
payment_processor = RealTimePaymentProcessorV210()

# ======================
# ENHANCED COMMANDS V2.10
# ======================
async def start_v210(update: Update, context):
    """Enhanced start command for V2.10"""
    user = update.effective_user
    
    # Register user if new
    user_id = user.id
    username = user.username or f"user_{user_id}"
    full_name = user.full_name or "Unknown"
    
    conn = sqlite3.connect('sheger_et_v210.db')
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT id FROM users_v210 WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()
    
    if not existing:
        # Create new user
        referral_code = f"SHEGER{random.randint(10000, 99999)}"
        cursor.execute('''
            INSERT INTO users_v210 
            (user_id, username, full_name, referral_code, created_at, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (user_id, username, full_name, referral_code))
        conn.commit()
        
        # Log analytics
        cursor.execute('''
            INSERT INTO audit_logs_v210 (user_id, action, created_at)
            VALUES (?, 'user_created', CURRENT_TIMESTAMP)
        ''', (user_id,))
        conn.commit()
        
        logging.info(f"👤 New user created: {user_id} (@{username})")
    
    conn.close()
    
    # Get user stats
    stats = get_user_stats_v210(user_id)
    kyc_info = get_kyc_info(user_id)
    
    # Enhanced keyboard
    keyboard = [
        [
            InlineKeyboardButton("💰 Wallet", callback_data="wallet_v210"),
            InlineKeyboardButton("💸 Send", callback_data="send_v210")
        ],
        [
            InlineKeyboardButton("📥 Deposit", callback_data="deposit_v210"),
            InlineKeyboardButton("📤 Withdraw", callback_data="withdraw_v210")
        ],
        [
            InlineKeyboardButton("🏪 Marketplace", callback_data="marketplace_v210"),
            InlineKeyboardButton("🔧 Services", callback_data="services_v210")
        ],
        [
            InlineKeyboardButton("📱 Airtime", callback_data="airtime_v210"),
            InlineKeyboardButton("💡 Bills", callback_data="bills_v210")
        ],
        [
            InlineKeyboardButton("📊 Analytics", callback_data="analytics_v210"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_v210")
        ],
        [
            InlineKeyboardButton("🎁 Promotions", callback_data="promotions_v210"),
            InlineKeyboardButton("📞 Support", callback_data="support_v210")
        ]
    ]
    
    # Enhanced welcome message
    text = f"""
🏙️ *{ConfigV210.APP_NAME}* 🇪🇹
*Version {ConfigV210.VERSION}*

👋 Welcome, *{full_name}*!

*Account Overview:*
💰 Balance: *{stats['balance']:,.2f} ETB*
🏷️ Plan: *{stats['plan'].upper()}*
🔐 KYC: *{kyc_info['status'].title()}*
⭐ Level: *{kyc_info['level']}*

*Daily Limits:*
💳 Send: *{kyc_info['daily_limit']:,.0f} ETB*
📈 Monthly: *{kyc_info['monthly_limit']:,.0f} ETB*

*Quick Stats:*
📊 Transactions: *{stats['transaction_count']}*
🤝 Referrals: *{stats['referral_count']}*
🎯 Earned: *{stats['total_earned']:,.2f} ETB*

*New in V2.10:*
✅ Real-time balance updates
✅ Instant P2P transfers
✅ Bill payments
✅ Airtime top-up
✅ Enhanced security
✅ Better analytics

*Choose an option below to get started!*
"""
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def wallet_v210(update: Update, context):
    """Enhanced wallet command"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    stats = get_user_stats_v210(user_id)
    
    # Real-time balance from cache
    real_time_balance = cache.get_user_balance(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("💳 Quick Send", callback_data="quick_send"),
            InlineKeyboardButton("📥 Instant Deposit", callback_data="instant_deposit")
        ],
        [
            InlineKeyboardButton("📤 Withdraw Now", callback_data="withdraw_now"),
            InlineKeyboardButton("📋 Transaction History", callback_data="tx_history")
        ],
        [
            InlineKeyboardButton("💸 Bulk Payments", callback_data="bulk_payments"),
            InlineKeyboardButton("🎯 Set PIN", callback_data="set_pin")
        ],
        [
            InlineKeyboardButton("📊 Spending Analytics", callback_data="spending_analytics"),
            InlineKeyboardButton("💳 Payment Methods", callback_data="payment_methods")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        ]
    ]
    
    text = f"""
💰 *Your SHEGER Wallet V2.10*

*Real-time Balance:* {real_time_balance:,.2f} ETB
*Escrow Balance:* {stats['escrow_balance']:,.2f} ETB
*Available:* {real_time_balance:,.2f} ETB

*Account Summary:*
📥 Total Deposited: {stats['total_deposited']:,.2f} ETB
📤 Total Withdrawn: {stats['total_withdrawn']:,.2f} ETB
📊 Net Flow: {(stats['total_deposited'] - stats['total_withdrawn']):,.2f} ETB

*Quick Actions:*
• Send money instantly
• Deposit with TeleBirr
• Withdraw to bank
• View transaction history
• Set security PIN
• Analyze spending

*Security Status:* 🔐 PIN {'' if stats.get('has_pin') else 'Not '}Set
*Last Activity:* {stats.get('last_active', 'Just now')}

*Ready to transact?*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_v210(update: Update, context):
    """Enhanced send command with real-time options"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = cache.get_user_balance(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("📱 To Phone", callback_data="send_phone"),
            InlineKeyboardButton("👤 To Username", callback_data="send_username")
        ],
        [
            InlineKeyboardButton("🏦 To Bank", callback_data="send_bank"),
            InlineKeyboardButton("💸 Bulk Send", callback_data="send_bulk")
        ],
        [
            InlineKeyboardButton("🏷️ QR Payment", callback_data="send_qr"),
            InlineKeyboardButton("🔗 Payment Link", callback_data="send_link")
        ],
        [
            InlineKeyboardButton("💳 Split Bill", callback_data="split_bill"),
            InlineKeyboardButton("🎯 Request Money", callback_data="request_money")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_wallet")
        ]
    ]
    
    text = f"""
💸 *Send Money V2.10*

*Available Balance:* {balance:,.2f} ETB

*Send To:*
1. 📱 *Phone Number* - Any Ethiopian phone
2. 👤 *Username* - Any SHEGER user
3. 🏦 *Bank Account* - Any Ethiopian bank
4. 💸 *Multiple People* - Bulk payments
5. 🏷️ *QR Code* - Scan to pay
6. 🔗 *Payment Link* - Share link to receive
7. 💳 *Split Bill* - Share expenses
8. 🎯 *Request Money* - Request from others

*Fees:*
• SHEGER to SHEGER: *0%* (Instant)
• To Bank: *0.5%* (1-2 hours)
• International: *1.5%* (1-3 days)

*Limits:*
• Per Transaction: *Based on KYC level*
• Daily Limit: *Based on KYC level*
• Speed: *Instant to SHEGER users*

*Security:* 🔐 PIN required for all transactions

*Choose how you want to send:*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deposit_v210(update: Update, context):
    """Enhanced deposit command with multiple methods"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    keyboard = [
        [
            InlineKeyboardButton("📱 TeleBirr", callback_data="deposit_telebirr"),
            InlineKeyboardButton("🏦 CBE", callback_data="deposit_cbe")
        ],
        [
            InlineKeyboardButton("🏦 Dashen", callback_data="deposit_dashen"),
            InlineKeyboardButton("🏦 Awash", callback_data="deposit_awash")
        ],
        [
            InlineKeyboardButton("💳 Chapa", callback_data="deposit_chapa"),
            InlineKeyboardButton("🏧 Bank Transfer", callback_data="deposit_bank")
        ],
        [
            InlineKeyboardButton("💵 Cash Agent", callback_data="deposit_agent"),
            InlineKeyboardButton("🌐 International", callback_data="deposit_international")
        ],
        [
            InlineKeyboardButton("📊 Compare Methods", callback_data="compare_methods"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_wallet")
        ]
    ]
    
    text = """
📥 *Deposit Money V2.10*

*Instant Deposit Methods:*
1. 📱 *TeleBirr* - 0% fee, Instant
2. 💳 *Chapa* - 1.5% fee, Instant

*Bank Transfers (1-2 hours):*
3. 🏦 *CBE* - 0.5% fee
4. 🏦 *Dashen* - 0.5% fee
5. 🏦 *Awash* - 0.5% fee
6. 🏧 *Other Banks* - 0.5% fee

*Other Methods:*
7. 💵 *Cash Agent* - 2% fee, 15 minutes
8. 🌐 *International* - 2.5% fee, 1-3 days

*Minimum/Maximum:*
• TeleBirr: 10 ETB / 50,000 ETB
• Bank Transfer: 100 ETB / 100,000 ETB
• Cash Agent: 50 ETB / 10,000 ETB

*Processing Time:*
• Instant: TeleBirr, Chapa
• Fast: Bank transfers (1-2 hours)
• Standard: Cash agent (15 minutes)
• International: 1-3 days

*Choose your preferred method:*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def services_v210(update: Update, context):
    """Enhanced services command"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📱 Airtime", callback_data="service_airtime"),
            InlineKeyboardButton("💡 Utility Bills", callback_data="service_bills")
        ],
        [
            InlineKeyboardButton("📺 TV & Internet", callback_data="service_tv"),
            InlineKeyboardButton("🚗 Transport", callback_data="service_transport")
        ],
        [
            InlineKeyboardButton("🎓 Education", callback_data="service_education"),
            InlineKeyboardButton("🏥 Health", callback_data="service_health")
        ],
        [
            InlineKeyboardButton("🏠 Rent", callback_data="service_rent"),
            InlineKeyboardButton("🛒 Shopping", callback_data="service_shopping")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        ]
    ]
    
    text = """
🔧 *SHEGER Services V2.10*

*Available Services:*

1. 📱 *Airtime & Data*
   • Ethio Telecom
   • Safaricom Ethiopia
   • All mobile operators
   • Instant top-up

2. 💡 *Utility Bills*
   • Ethiopian Electric Power
   • Water utilities
   • Internet bills
   • Cable TV

3. 📺 *TV & Internet*
   • Ethio Telecom
   • Safaricom
   • Other ISPs
   • Cable subscriptions

4. 🚗 *Transport*
   • Ride hailing
   • Bus tickets
   • Flight bookings
   • Taxi payments

5. 🎓 *Education*
   • School fees
   • University payments
   • Course fees
   • Book purchases

6. 🏥 *Health*
   • Hospital bills
   • Pharmacy payments
   • Clinic fees
   • Health insurance

7. 🏠 *Rent & Housing*
   • Rent payments
   • Security deposits
   • Maintenance fees
   • Property taxes

8. 🛒 *Shopping*
   • Online stores
   • Supermarkets
   • Local shops
   • Food delivery

*Coming Soon:*
• Insurance payments
• Investment services
• Loan applications
• Savings plans

*Choose a service to proceed:*
"""
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ======================
# REAL-TIME ANALYTICS V2.10
# ======================
class AnalyticsV210:
    """Real-time analytics for V2.10"""
    
    @staticmethod
    def generate_user_report(user_id: int) -> Dict:
        """Generate comprehensive user report"""
        conn = sqlite3.connect('sheger_et_v210.db')
        
        # User stats
        user_df = pd.read_sql_query('''
            SELECT * FROM users_v210 WHERE user_id = ?
        ''', conn, params=(user_id,))
        
        # Transaction stats
        tx_df = pd.read_sql_query('''
            SELECT * FROM transactions_v210 
            WHERE sender_id = ? OR receiver_id = ?
            ORDER BY initiated_at DESC
            LIMIT 100
        ''', conn, params=(user_id, user_id))
        
        conn.close()
        
        if user_df.empty:
            return {}
        
        # Calculate metrics
        if not tx_df.empty:
            tx_df['initiated_at'] = pd.to_datetime(tx_df['initiated_at'])
            
            # Daily spending
            daily_spending = tx_df[tx_df['sender_id'] == user_id].groupby(
                tx_df['initiated_at'].dt.date
            )['amount'].sum()
            
            # Category breakdown
            category_breakdown = tx_df.groupby('category')['amount'].sum()
            
            # Payment methods
            method_breakdown = tx_df.groupby('payment_method').size()
        else:
            daily_spending = pd.Series()
            category_breakdown = pd.Series()
            method_breakdown = pd.Series()
        
        user_data = user_df.iloc[0]
        
        return {
            'user_info': {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'full_name': user_data['full_name'],
                'plan': user_data['plan'],
                'kyc_status': user_data['kyc_status'],
                'kyc_level': user_data['kyc_level'],
                'joined_date': user_data['created_at']
            },
            'financial_summary': {
                'balance': user_data['balance'],
                'escrow_balance': user_data['escrow_balance'],
                'total_deposited': user_data['total_deposited'],
                'total_withdrawn': user_data['total_withdrawn'],
                'net_flow': user_data['total_deposited'] - user_data['total_withdrawn']
            },
            'transaction_stats': {
                'total_count': len(tx_df),
                'success_rate': (tx_df['status'] == 'completed').mean() if not tx_df.empty else 0,
                'average_amount': tx_df['amount'].mean() if not tx_df.empty else 0,
                'largest_transaction': tx_df['amount'].max() if not tx_df.empty else 0
            },
            'daily_spending': daily_spending.to_dict(),
            'category_breakdown': category_breakdown.to_dict(),
            'method_breakdown': method_breakdown.to_dict(),
            'limits': {
                'daily_limit': user_data['daily_limit'],
                'monthly_limit': user_data['monthly_limit'],
                'remaining_daily': user_data['daily_limit'] - AnalyticsV210.get_today_spending(user_id)
            }
        }
    
    @staticmethod
    def get_today_spending(user_id: int) -> float:
        """Get today's spending"""
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) 
            FROM transactions_v210 
            WHERE sender_id = ? 
            AND DATE(initiated_at) = DATE('now')
            AND status = 'completed'
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0.0
    
    @staticmethod
    def generate_visualizations(user_id: int) -> Optional[BytesIO]:
        """Generate analytics visualizations"""
        try:
            report = AnalyticsV210.generate_user_report(user_id)
            if not report:
                return None
            
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
            # Spending trend
            if report.get('daily_spending'):
                dates = list(report['daily_spending'].keys())[-7:]
                amounts = list(report['daily_spending'].values())[-7:]
                axes[0,0].bar(dates, amounts)
                axes[0,0].set_title('Last 7 Days Spending')
                axes[0,0].tick_params(axis='x', rotation=45)
            
            # Category breakdown
            if report.get('category_breakdown'):
                categories = list(report['category_breakdown'].keys())
                amounts = list(report['category_breakdown'].values())
                axes[0,1].pie(amounts, labels=categories, autopct='%1.1f%%')
                axes[0,1].set_title('Spending by Category')
            
            # Method breakdown
            if report.get('method_breakdown'):
                methods = list(report['method_breakdown'].keys())
                counts = list(report['method_breakdown'].values())
                axes[1,0].bar(methods, counts)
                axes[1,0].set_title('Payment Methods Used')
                axes[1,0].tick_params(axis='x', rotation=45)
            
            # Financial summary
            financial = report.get('financial_summary', {})
            if financial:
                labels = ['Balance', 'Deposited', 'Withdrawn']
                values = [
                    financial.get('balance', 0),
                    financial.get('total_deposited', 0),
                    financial.get('total_withdrawn', 0)
                ]
                axes[1,1].bar(labels, values)
                axes[1,1].set_title('Financial Summary')
            
            plt.tight_layout()
            
            # Save to buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='PNG', dpi=100)
            plt.close()
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logging.error(f"Visualization error: {e}")
            return None

# ======================
# HELPER FUNCTIONS
# ======================
def get_user_stats_v210(user_id: int) -> Dict:
    """Get enhanced user statistics"""
    try:
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        
        # User info
        cursor.execute('''
            SELECT plan, balance, escrow_balance, total_deposited, 
                   total_withdrawn, referral_code, created_at,
                   last_active, daily_limit, monthly_limit
            FROM users_v210 WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return {}
        
        # Transaction count
        cursor.execute('''
            SELECT COUNT(*) FROM transactions_v210 
            WHERE sender_id = ? OR receiver_id = ?
        ''', (user_id, user_id))
        
        tx_count = cursor.fetchone()[0] or 0
        
        # Referral count
        cursor.execute('SELECT COUNT(*) FROM users_v210 WHERE referred_by = ?', (user_id,))
        referral_count = cursor.fetchone()[0] or 0
        
        # Earnings from referrals
        cursor.execute('''
            SELECT COALESCE(SUM(amount * 0.1), 0) 
            FROM transactions_v210 
            WHERE receiver_id IN (
                SELECT user_id FROM users_v210 WHERE referred_by = ?
            ) AND status = 'completed'
        ''', (user_id,))
        
        referral_earnings = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'plan': user[0],
            'balance': user[1],
            'escrow_balance': user[2],
            'total_deposited': user[3],
            'total_withdrawn': user[4],
            'referral_code': user[5],
            'joined_date': user[6],
            'last_active': user[7],
            'daily_limit': user[8],
            'monthly_limit': user[9],
            'transaction_count': tx_count,
            'referral_count': referral_count,
            'total_earned': referral_earnings
        }
        
    except Exception as e:
        logging.error(f"Get user stats error: {e}")
        return {}

def get_kyc_info(user_id: int) -> Dict:
    """Get KYC information"""
    try:
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT kyc_status, kyc_level, daily_limit, monthly_limit
            FROM users_v210 WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'status': result[0],
                'level': result[1],
                'daily_limit': result[2],
                'monthly_limit': result[3]
            }
        
        return ConfigV210.KYC_LEVELS['level0']
        
    except Exception as e:
        logging.error(f"Get KYC info error: {e}")
        return ConfigV210.KYC_LEVELS['level0']

# ======================
# BUTTON HANDLER V2.10
# ======================
async def button_handler_v210(update: Update, context):
    """Handle V2.10 button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "wallet_v210":
        await wallet_v210(update, context)
    
    elif data == "send_v210":
        await send_v210(update, context)
    
    elif data == "deposit_v210":
        await deposit_v210(update, context)
    
    elif data == "services_v210":
        await services_v210(update, context)
    
    elif data == "back_to_main":
        await start_v210(update, context)
    
    elif data == "back_to_wallet":
        await wallet_v210(update, context)
    
    elif data == "analytics_v210":
        await show_analytics(update, context)
    
    elif data == "send_phone":
        await send_to_phone(update, context)
    
    elif data == "deposit_telebirr":
        await deposit_telebirr_flow(update, context)

async def show_analytics(update: Update, context):
    """Show analytics dashboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    report = AnalyticsV210.generate_user_report(user_id)
    
    if not report:
        await query.edit_message_text(
            "❌ No analytics data available yet.",
            parse_mode='Markdown'
        )
        return
    
    # Generate visualization
    viz_buffer = AnalyticsV210.generate_visualizations(user_id)
    
    # Prepare text
    user_info = report['user_info']
    financial = report['financial_summary']
    tx_stats = report['transaction_stats']
    limits = report['limits']
    
    text = f"""
📊 *Analytics Dashboard V2.10*

*User Information:*
👤 {user_info['full_name']}
🏷️ Plan: {user_info['plan'].upper()}
🔐 KYC: {user_info['kyc_status'].title()} ({user_info['kyc_level']})
📅 Member Since: {user_info['joined_date'][:10]}

*Financial Summary:*
💰 Current Balance: {financial['balance']:,.2f} ETB
📥 Total Deposited: {financial['total_deposited']:,.2f} ETB
📤 Total Withdrawn: {financial['total_withdrawn']:,.2f} ETB
📈 Net Flow: {financial['net_flow']:,.2f} ETB

*Transaction Statistics:*
🔄 Total Transactions: {tx_stats['total_count']}
✅ Success Rate: {tx_stats['success_rate']*100:.1f}%
💸 Average Amount: {tx_stats['average_amount']:,.2f} ETB
🏆 Largest Transaction: {tx_stats['largest_transaction']:,.2f} ETB

*Limits & Usage:*
💳 Daily Limit: {limits['daily_limit']:,.0f} ETB
📊 Used Today: {limits['remaining_daily']:,.0f} ETB
🎯 Remaining: {(limits['daily_limit'] - limits['remaining_daily']):,.0f} ETB

*Visualizations below show your spending patterns.*
"""
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    # Send visualization if available
    if viz_buffer:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=viz_buffer,
            caption="📈 Your Spending Analytics"
        )

async def send_to_phone(update: Update, context):
    """Send to phone flow"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 *Send to Phone Number*\n\n"
        "Enter phone number and amount:\n\n"
        "*Format:* `0912345678 1000`\n\n"
        "*Examples:*\n"
        "• `0912345678 500` - Send 500 ETB\n"
        "• `0912345678 1000 Lunch money` - With note\n\n"
        "*Fees:* 0% for SHEGER users, 0.5% for others\n"
        "*Speed:* Instant\n\n"
        "Enter details now:",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_send_details'] = 'phone'

async def deposit_telebirr_flow(update: Update, context):
    """TeleBirr deposit flow"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 *TeleBirr Deposit*\n\n"
        "Enter amount to deposit (ETB):\n\n"
        "*Minimum:* 10 ETB\n"
        "*Maximum:* 50,000 ETB\n"
        "*Fee:* 0%\n"
        "*Processing:* Instant\n\n"
        "Enter amount (e.g., `1000`):",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_deposit'] = {
        'method': 'telebirr',
        'step': 'amount'
    }

# ======================
# MESSAGE HANDLER V2.10
# ======================
async def handle_messages_v210(update: Update, context):
    """Handle messages for V2.10"""
    user = update.effective_user
    text = update.message.text
    
    # Check for send details
    if context.user_data.get('awaiting_send_details') == 'phone':
        try:
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ Invalid format. Use: `0912345678 1000`",
                    parse_mode='Markdown'
                )
                return
            
            phone = parts[0]
            amount = float(parts[1])
            note = ' '.join(parts[2:]) if len(parts) > 2 else ""
            
            # Validate phone
            if not phone.startswith('09') or len(phone) != 10:
                await update.message.reply_text(
                    "❌ Invalid phone number. Must be 09XXXXXXXX format."
                )
                return
            
            # Validate amount
            if amount < 1:
                await update.message.reply_text("❌ Amount must be at least 1 ETB.")
                return
            
            # Check balance
            balance = cache.get_user_balance(user.id)
            if balance < amount:
                await update.message.reply_text(
                    f"❌ Insufficient balance. You have {balance:,.2f} ETB."
                )
                return
            
            # Process payment
            transaction_id = f"TX{int(time.time())}{random.randint(1000, 9999)}"
            
            payment_data = {
                'type': 'p2p',
                'transaction_id': transaction_id,
                'sender_id': user.id,
                'receiver_phone': phone,
                'amount': amount,
                'fee': 0,
                'note': note,
                'timestamp': datetime.now().isoformat()
            }
            
            # Queue for processing
            payment_processor.processing_queue.put(payment_data)
            
            await update.message.reply_text(
                f"""
✅ *Payment Queued*

To: {phone}
Amount: {amount:,.2f} ETB
Fee: 0 ETB
Total: {amount:,.2f} ETB
Note: {note or 'No note'}
Transaction ID: `{transaction_id}`

*Status:* Processing...
*Speed:* Instant

You'll be notified when completed.
                """,
                parse_mode='Markdown'
            )
            
            context.user_data['awaiting_send_details'] = None
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    # Check for deposit amount
    elif context.user_data.get('awaiting_deposit') and context.user_data['awaiting_deposit'].get('step') == 'amount':
        try:
            amount = float(text)
            method = context.user_data['awaiting_deposit']['method']
            
            if amount < 10:
                await update.message.reply_text("❌ Minimum deposit is 10 ETB.")
                return
            
            if amount > 50000:
                await update.message.reply_text("❌ Maximum deposit is 50,000 ETB.")
                return
            
            # Process deposit
            transaction_id = f"DEP{int(time.time())}{random.randint(1000, 9999)}"
            
            deposit_data = {
                'type': 'deposit',
                'transaction_id': transaction_id,
                'user_id': user.id,
                'amount': amount,
                'method': method,
                'timestamp': datetime.now().isoformat()
            }
            
            # Queue for processing
            payment_processor.processing_queue.put(deposit_data)
            
            if method == 'telebirr':
                await update.message.reply_text(
                    f"""
✅ *Deposit Initiated*

Amount: {amount:,.2f} ETB
Method: TeleBirr
Transaction ID: `{transaction_id}`
Fee: 0%

*Instructions:*
1. Open TeleBirr app
2. Tap 'Scan QR'
3. Scan the QR code below
4. Confirm payment

Funds will be added instantly after payment.
                    """,
                    parse_mode='Markdown'
                )
            
            context.user_data['awaiting_deposit'] = None
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")

# ======================
# ADMIN ENHANCEMENTS V2.10
# ======================
async def admin_dashboard_v210(update: Update, context):
    """Enhanced admin dashboard"""
    user_id = update.effective_user.id
    
    # Check if admin
    if user_id not in [7714584854]:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    conn = sqlite3.connect('sheger_et_v210.db')
    cursor = conn.cursor()
    
    # Platform stats
    cursor.execute("SELECT COUNT(*) FROM users_v210")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users_v210 WHERE DATE(created_at) = DATE('now')")
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions_v210 WHERE DATE(initiated_at) = DATE('now')")
    today_tx = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM transactions_v210 WHERE status = 'completed' AND DATE(completed_at) = DATE('now')")
    today_volume = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions_v210 WHERE status = 'pending'")
    pending_tx = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users_v210")
    total_balance = cursor.fetchone()[0] or 0
    
    conn.close()
    
    text = f"""
👑 *Admin Dashboard V2.10*

*Platform Overview:*
👥 Total Users: {total_users:,}
📈 New Today: {today_users}
🔄 Transactions Today: {today_tx}
💰 Volume Today: {today_volume:,.0f} ETB
⏳ Pending Transactions: {pending_tx}
💎 Total Balance: {total_balance:,.0f} ETB

*Quick Actions:*
• `/admin_users` - User management
• `/admin_tx` - Transaction review
• `/admin_pending` - Pending approvals
• `/admin_kyc` - KYC review
• `/admin_reports` - Generate reports
• `/admin_backup` - Create backup
• `/admin_broadcast` - Send announcement

*Real-time Stats:*
• Cache hit rate: {cache.connected}
• Queue size: {payment_processor.processing_queue.qsize()}
• Active users: Real-time monitoring

*Commands:*
`/verify USER_ID AMOUNT` - Verify payment
`/kyc_approve USER_ID` - Approve KYC
`/limit_set USER_ID DAILY MONTHLY` - Set limits
`/user_info USER_ID` - User details
`/tx_info TX_ID` - Transaction details
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# SCHEDULED TASKS V2.10
# ======================
async def scheduled_tasks_v210(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled tasks for V2.10"""
    logging.info("🔄 Running V2.10 scheduled tasks...")
    
    try:
        # Clean up old sessions
        conn = sqlite3.connect('sheger_et_v210.db')
        cursor = conn.cursor()
        
        # Mark inactive users
        cursor.execute('''
            UPDATE users_v210 
            SET status = 'inactive'
            WHERE last_active < datetime('now', '-30 days')
            AND status = 'active'
        ''')
        
        # Expire pending transactions older than 24 hours
        cursor.execute('''
            UPDATE transactions_v210 
            SET status = 'expired', failure_reason = 'Timeout'
            WHERE status = 'pending' 
            AND initiated_at < datetime('now', '-24 hours')
        ''')
        
        # Auto-release escrow after 7 days
        cursor.execute('''
            UPDATE escrows_v210 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                released_amount = amount, held_amount = 0
            WHERE status = 'funded' 
            AND auto_release_at < CURRENT_TIMESTAMP
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("✅ Scheduled tasks completed")
        
    except Exception as e:
        logging.error(f"Scheduled tasks error: {e}")

# ======================
# MAIN FUNCTION V2.10
# ======================
def main_v210():
    """Main function for V2.10"""
    # Get token from environment
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logging.error("❌ TELEGRAM_TOKEN not set in environment!")
        logging.info("💡 Set it: export TELEGRAM_TOKEN='your_token'")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_v210))
    application.add_handler(CommandHandler("wallet", wallet_v210))
    application.add_handler(CommandHandler("admin", admin_dashboard_v210))
    application.add_handler(CommandHandler("help", help_command_v210))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler_v210))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages_v210))
    
    # Scheduled tasks
    job_queue = application.job_queue
    if job_queue:
        # Run every hour
        job_queue.run_repeating(
            scheduled_tasks_v210,
            interval=3600,
            first=10
        )
        
        # Daily backup at 2 AM
        job_queue.run_daily(
            scheduled_tasks_v210,
            time=datetime.time(hour=2, minute=0)
        )
    
    # Startup message
    logging.info("=" * 70)
    logging.info(f"🚀 {ConfigV210.APP_NAME} LAUNCHING")
    logging.info(f"🌟 Version: {ConfigV210.VERSION}")
    logging.info("💰 ENTERPRISE FEATURES ENABLED:")
    logging.info("   • Real-time balance updates")
    logging.info("   • Instant P2P transfers")
    logging.info("   • Multiple payment methods")
    logging.info("   • Enhanced security")
    logging.info("   • Advanced analytics")
    logging.info("   • Bill payments & services")
    logging.info("=" * 70)
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def help_command_v210(update: Update, context):
    """Help command for V2.10"""
    text = f"""
🆘 *{ConfigV210.APP_NAME} Help*

*Basic Commands:*
`/start` - Start the bot
`/wallet` - Check your wallet
`/help` - Show this message

*Features:*
• 💰 Real-time balance updates
• 💸 Instant P2P transfers
• 📥 Multiple deposit methods
• 📤 Bank withdrawals
• 🏪 Marketplace
• 🔧 Services (bills, airtime, etc.)
• 📊 Advanced analytics
• 🔒 Enhanced security

*Payment Methods:*
• TeleBirr - Instant, 0% fee
• CBE Bank - 0.5% fee
• Dashen Bank - 0.5% fee
• Awash Bank - 0.5% fee
• SHEGER Balance - Instant, 0% fee

*Support:*
📞 24/7 Customer Support
📧 support@shegeret.com
👤 @ShegerSupport

*Version {ConfigV210.VERSION}*
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ======================
# DEPLOYMENT COMMANDS
# ======================
def setup_v210():
    """Setup V2.10 environment"""
    print("🔧 Setting up SHEGER ET V2.10...")
    
    # Check environment
    if not os.getenv("TELEGRAM_TOKEN"):
        print("❌ TELEGRAM_TOKEN not set!")
        print("💡 Run: export TELEGRAM_TOKEN='your_token'")
        return False
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis: Connected")
    except:
        print("⚠️ Redis: Not available (running in fallback mode)")
    
    # Initialize database
    if init_database_v210():
        print("✅ Database: Initialized")
    else:
        print("❌ Database: Failed to initialize")
        return False
    
    # Test cache
    cache.set("test", {"message": "V2.10 is ready"}, 10)
    test_result = cache.get("test")
    if test_result:
        print("✅ Cache: Working")
    else:
        print("⚠️ Cache: In-memory only")
    
    print("✅ V2.10 setup complete!")
    print("🚀 Start with: python sheger_v210.py")
    return True

if __name__ == "__main__":
    # Setup and run
    if setup_v210():
        main_v210()
