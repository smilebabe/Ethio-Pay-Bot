#!/usr/bin/env python3
"""
SHEGER ET V2.10 PRODUCTION - Ethiopian Super App with Complete Tier System
Production Ready with PostgreSQL Database, Marketing, Analytics & Tier Management
"""

import os
import json
import logging
import psycopg2
import psycopg2.extras
import shutil
import asyncio
import random
import string
import csv
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ======================
# POSTGRESQL CONFIGURATION
# ======================
DATABASE_URL = os.getenv("DATABASE_URL=postgresql://postgres:nkIgStTDGjbqHYarRAyheKsTOXwcHKpa@postgres.railway.internal:5432/railway")
# If using individual parameters (for backward compatibility)
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "sheger_et")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

TELEBIRR = os.getenv("TELEBIRR_NUMBER", "0961393001")
CBE = os.getenv("CBE_ACCOUNT", "1000645865603")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7714584854"))

SUPPORT = os.getenv("SUPPORT_CHANNEL", "@ShegerESupport")
PAYMENTS = os.getenv("PAYMENTS_CHANNEL", "@ShegerPayments")
SALES = os.getenv("SALES_CHANNEL", "@ShegerESales")
NEWS = os.getenv("NEWS_CHANNEL", "@ShegeErNews")

BOT_NAME = os.getenv("BOT_NAME", "SHEGER ET")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@ShegerETBot")
BOT_SLOGAN = os.getenv("BOT_SLOGAN", "Ethiopia's All-in-One Super App")

# Backup Configuration
BACKUP_DIR = os.getenv("BACKUP_DIR", "sheger_backups_v2")

# ======================
# ENHANCED LOGGING
# ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('sheger_v2_postgres.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ======================
# POSTGRESQL DATABASE INITIALIZATION WITH COMPLETE TIER SYSTEM
# ======================
def get_db_connection():
    """Get PostgreSQL database connection with dict cursor"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

def init_database_v2():
    """Initialize PostgreSQL database with marketing, analytics and tier system"""
    try:
        # Create backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Enable extensions if needed
        cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        
        # Enhanced users table WITH TIER COLUMNS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                full_name TEXT,
                phone VARCHAR(20),
                email VARCHAR(255),
                plan VARCHAR(50) DEFAULT 'basic',
                balance DECIMAL(15,2) DEFAULT 0,
                referral_code VARCHAR(50) UNIQUE,
                referred_by BIGINT,
                total_spent DECIMAL(15,2) DEFAULT 0,
                total_earned DECIMAL(15,2) DEFAULT 0,
                join_source VARCHAR(100),
                campaign_id VARCHAR(100),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_payment TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active',
                metadata JSONB DEFAULT '{}',
                tier VARCHAR(50) DEFAULT 'basic',
                tier_expires_at TIMESTAMP,
                monthly_transactions INTEGER DEFAULT 0,
                monthly_listings INTEGER DEFAULT 0,
                family_owner_id BIGINT,
                role VARCHAR(50) DEFAULT 'member'
            )
        ''')
        
        # Enhanced payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                plan VARCHAR(50),
                amount DECIMAL(15,2),
                status VARCHAR(50) DEFAULT 'pending',
                reference_code VARCHAR(100) UNIQUE,
                payment_method VARCHAR(50),
                payment_proof TEXT,
                admin_notes TEXT,
                verified_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                expires_at TIMESTAMP,
                campaign_id VARCHAR(100),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Marketing campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                code VARCHAR(100) UNIQUE,
                type VARCHAR(50), -- referral, discount, promo, tier_upgrade
                discount_percent DECIMAL(5,2),
                discount_amount DECIMAL(15,2),
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                starts_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                conditions JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(100), -- user_join, payment, upgrade, referral, tier_upgrade, tier_downgrade
                user_id BIGINT,
                data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                title VARCHAR(255),
                message TEXT,
                notification_type VARCHAR(50), -- payment, reminder, promo, update, tier_limit
                is_read BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # TIER LIMITS TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tier_limits (
                tier VARCHAR(50) PRIMARY KEY,
                max_transactions INTEGER,
                max_listings INTEGER,
                max_balance DECIMAL(15,2),
                daily_limit DECIMAL(15,2),
                features JSONB
            )
        ''')
        
        # Family/Team management table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                owner_id BIGINT NOT NULL,
                member_id BIGINT UNIQUE NOT NULL,
                role VARCHAR(50) DEFAULT 'member', -- owner, manager, member, viewer
                spending_limit DECIMAL(15,2) DEFAULT 0,
                permissions JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Marketplace listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketplace_listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                title VARCHAR(255),
                description TEXT,
                category VARCHAR(100),
                price DECIMAL(15,2),
                images JSONB, -- JSON array of image paths
                status VARCHAR(50) DEFAULT 'active',
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Job listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                title VARCHAR(255),
                description TEXT,
                category VARCHAR(100),
                salary DECIMAL(15,2),
                location TEXT,
                job_type VARCHAR(50), -- full_time, part_time, contract, remote
                status VARCHAR(50) DEFAULT 'active',
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Property listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS property_listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                title VARCHAR(255),
                description TEXT,
                property_type VARCHAR(50), -- house, apartment, land, commercial
                price DECIMAL(15,2),
                location TEXT,
                bedrooms INTEGER,
                bathrooms INTEGER,
                area DECIMAL(10,2),
                images JSONB, -- JSON array of image paths
                status VARCHAR(50) DEFAULT 'active',
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_users_ref_code ON users(referral_code)',
            'CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)',
            'CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier)',
            'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_payments_campaign ON payments(campaign_id)',
            'CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)',
            'CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event_type, created_at)',
            'CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_family_owner ON family_members(owner_id)',
            'CREATE INDEX IF NOT EXISTS idx_family_member ON family_members(member_id)',
            'CREATE INDEX IF NOT EXISTS idx_marketplace_user ON marketplace_listings(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_marketplace_status ON marketplace_listings(status)',
            'CREATE INDEX IF NOT EXISTS idx_marketplace_category ON marketplace_listings(category)',
            'CREATE INDEX IF NOT EXISTS idx_jobs_user ON job_listings(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_jobs_category ON job_listings(category)',
            'CREATE INDEX IF NOT EXISTS idx_properties_user ON property_listings(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_properties_type ON property_listings(property_type)',
            'CREATE INDEX IF NOT EXISTS idx_campaigns_code ON campaigns(code)',
            'CREATE INDEX IF NOT EXISTS idx_campaigns_active ON campaigns(is_active) WHERE is_active = true',
            'CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id) WHERE is_read = false'
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        # Insert tier limits data
        tier_limits_data = [
            ('basic', 10, 5, 10000, 5000, 
             '{"payment_methods": ["telebirr"], "verification": "manual", "support": "community", "api_access": false}'),
            ('advanced', 100, 50, 100000, 50000, 
             '{"payment_methods": ["telebirr", "cbe", "bank"], "verification": "semi_auto", "support": "priority", "api_access": false}'),
            ('pro', 999999, 999999, 9999999, 500000, 
             '{"payment_methods": ["telebirr", "cbe", "bank", "visa", "mastercard"], "verification": "instant", "support": "24/7_dedicated", "api_access": true}')
        ]
        
        cursor.executemany('''
            INSERT INTO tier_limits (tier, max_transactions, max_listings, max_balance, daily_limit, features) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tier) DO UPDATE SET
            max_transactions = EXCLUDED.max_transactions,
            max_listings = EXCLUDED.max_listings,
            max_balance = EXCLUDED.max_balance,
            daily_limit = EXCLUDED.daily_limit,
            features = EXCLUDED.features
        ''', tier_limits_data)
        
        conn.commit()
        logger.info("✅ PostgreSQL V2 Database initialized with complete tier system")
        
        # Create default campaigns
        create_default_campaigns()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """Execute SQL query with proper error handling"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute(query, params or ())
        
        if commit:
            conn.commit()
        
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None
        
        cursor.close()
        return result
        
    except Exception as e:
        logger.error(f"Query failed: {e}, Query: {query}, Params: {params}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def create_default_campaigns():
    """Create default marketing campaigns"""
    try:
        now = datetime.now().isoformat()
        later_30 = (datetime.now() + timedelta(days=30)).isoformat()
        later_90 = (datetime.now() + timedelta(days=90)).isoformat()
        later_365 = (datetime.now() + timedelta(days=365)).isoformat()
        later_60 = (datetime.now() + timedelta(days=60)).isoformat()
        
        # Launch campaign
        execute_query('''
            INSERT INTO campaigns 
            (name, code, type, discount_percent, max_uses, starts_at, expires_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        ''', (
            'Launch Special',
            'SHEGERLAUNCH',
            'discount',
            100,  # 100% discount = first month free
            1000,
            now,
            later_30,
            True
        ), commit=True)
        
        # Referral campaign
        execute_query('''
            INSERT INTO campaigns 
            (name, code, type, discount_amount, max_uses, starts_at, expires_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        ''', (
            'Referral Bonus',
            'REFER10',
            'referral',
            14.9,  # 10% of 149 ETB
            10000,
            now,
            later_365,
            True
        ), commit=True)
        
        # Tier upgrade promotions
        execute_query('''
            INSERT INTO campaigns 
            (name, code, type, discount_percent, max_uses, starts_at, expires_at, is_active, conditions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        ''', (
            'First Upgrade Special',
            'UPGRADE50',
            'tier_upgrade',
            50,  # 50% off first upgrade
            500,
            now,
            later_90,
            True,
            json.dumps({"min_tier": "basic", "max_uses_per_user": 1})
        ), commit=True)
        
        execute_query('''
            INSERT INTO campaigns 
            (name, code, type, discount_percent, max_uses, starts_at, expires_at, is_active, conditions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        ''', (
            'Pro Upgrade Bundle',
            'PROBUNDLE',
            'tier_upgrade',
            30,  # 30% off Pro upgrade
            200,
            now,
            later_60,
            True,
            json.dumps({"min_tier": "advanced", "max_uses_per_user": 1})
        ), commit=True)
        
        logger.info("✅ Default campaigns created")
        
    except Exception as e:
        logger.error(f"Error creating campaigns: {e}")

# Initialize database
init_database_v2()

# ======================
# TIERED FEATURE SYSTEM
# ======================
class TierSystem:
    """Manage tiered features for SHEGER ET"""
    
    TIERS = {
        'basic': {
            'price': 0,
            'color': '🟢',
            'max_users': 1000,
            'storage': 'SQLite',
            'support': 'Community',
            'uptime': '99%',
            'max_family_members': 0,
            'bulk_operations': False,
            'api_access': False,
            'fee': 2.5,
            'commission_rate': 10,
            'withdrawal_fee': 1.0
        },
        'advanced': {
            'price': 149,
            'color': '🟡',
            'max_users': 10000,
            'storage': 'SQLite + Cloud Sync',
            'support': 'Priority Email',
            'uptime': '99.5%',
            'max_family_members': 5,
            'bulk_operations': False,
            'api_access': False,
            'fee': 1.5,
            'commission_rate': 12,
            'withdrawal_fee': 0.5
        },
        'pro': {
            'price': 999,
            'color': '🔴',
            'max_users': 'Unlimited',
            'storage': 'PostgreSQL Cloud',
            'support': '24/7 Phone + Dedicated',
            'uptime': '99.9%',
            'max_family_members': 999999,
            'bulk_operations': True,
            'api_access': True,
            'fee': 0.8,
            'commission_rate': 15,
            'withdrawal_fee': 0.1
        }
    }
    
    @staticmethod
    def get_user_tier(user_id: int) -> str:
        """Get user's current tier"""
        result = execute_query(
            'SELECT tier FROM users WHERE user_id = %s',
            (user_id,),
            fetchone=True
        )
        return result['tier'] if result else 'basic'
    
    @staticmethod
    def check_limit(user_id: int, action: str) -> dict:
        """Check if user can perform action based on tier"""
        result = execute_query('''
            SELECT u.tier, u.monthly_transactions, u.monthly_listings,
                   tl.max_transactions, tl.max_listings
            FROM users u
            LEFT JOIN tier_limits tl ON u.tier = tl.tier
            WHERE u.user_id = %s
        ''', (user_id,), fetchone=True)
        
        if not result:
            return {'allowed': False, 'reason': 'User not found'}
        
        tier = result['tier'] or 'basic'
        
        if action == 'payment' and result['monthly_transactions'] >= result['max_transactions']:
            return {
                'allowed': False,
                'reason': f'Monthly transaction limit reached ({result["monthly_transactions"]}/{result["max_transactions"]})',
                'upgrade': 'advanced' if tier == 'basic' else 'pro'
            }
        
        if action == 'listing' and result['monthly_listings'] >= result['max_listings']:
            return {
                'allowed': False,
                'reason': f'Monthly listing limit reached ({result["monthly_listings"]}/{result["max_listings"]})',
                'upgrade': 'advanced' if tier == 'basic' else 'pro'
            }
        
        return {'allowed': True, 'tier': tier}
    
    @staticmethod
    def increment_counter(user_id: int, action: str):
        """Increment user's monthly counter"""
        if action == 'payment':
            execute_query('''
                UPDATE users SET monthly_transactions = monthly_transactions + 1 
                WHERE user_id = %s
            ''', (user_id,), commit=True)
        elif action == 'listing':
            execute_query('''
                UPDATE users SET monthly_listings = monthly_listings + 1 
                WHERE user_id = %s
            ''', (user_id,), commit=True)
    
    @staticmethod
    def reset_monthly_counters():
        """Reset all monthly counters (run monthly)"""
        execute_query(
            'UPDATE users SET monthly_transactions = 0, monthly_listings = 0',
            commit=True
        )
        logger.info("🔄 Monthly tier counters reset")

# ======================
# HELPER FUNCTIONS
# ======================
def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code"""
    prefix = "SHEGER"
    unique = f"{user_id:06d}"[-6:]
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{unique}{chars}"

def create_or_update_user_v2(user_id: int, username: str, full_name: str, source: str = "bot"):
    """Create or update user with enhanced tracking"""
    try:
        # Check if user exists
        user = execute_query(
            "SELECT id, referral_code FROM users WHERE user_id = %s",
            (user_id,),
            fetchone=True
        )
        
        if user:
            # Update existing user
            execute_query('''
                UPDATE users 
                SET username = %s, full_name = %s, last_active = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (username, full_name, user_id), commit=True)
            
            referral_code = user['referral_code']
            
        else:
            # Create new user with referral code
            referral_code = generate_referral_code(user_id)
            
            execute_query('''
                INSERT INTO users 
                (user_id, username, full_name, referral_code, join_source, joined_at, last_active, tier)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'basic')
            ''', (user_id, username, full_name, referral_code, source), commit=True)
            
            # Log analytics
            execute_query('''
                INSERT INTO analytics (event_type, user_id, data)
                VALUES (%s, %s, %s)
            ''', ('user_join', user_id, json.dumps({'source': source})), commit=True)
            
            logger.info(f"👤 V2 User created: {user_id} (@{username}) from {source}")
        
        return referral_code
        
    except Exception as e:
        logger.error(f"Error creating user V2: {e}")
        return None

def get_user_stats(user_id: int) -> Dict:
    """Get comprehensive user statistics"""
    try:
        # User info
        user = execute_query('''
            SELECT plan, total_spent, total_earned, balance, referral_code, joined_at,
                   tier, monthly_transactions, monthly_listings
            FROM users WHERE user_id = %s
        ''', (user_id,), fetchone=True)
        
        if not user:
            return {}
        
        # Referral stats
        referral_stats = execute_query('''
            SELECT COUNT(*) as referred_count, 
                   SUM(total_spent) as referred_revenue
            FROM users WHERE referred_by = %s
        ''', (user_id,), fetchone=True)
        
        # Payment history
        payment_stats = execute_query('''
            SELECT COUNT(*) as total_payments,
                   SUM(amount) as total_verified_amount
            FROM payments 
            WHERE user_id = %s AND status = 'verified'
        ''', (user_id,), fetchone=True)
        
        # Get tier limits
        tier_limits = execute_query(
            'SELECT * FROM tier_limits WHERE tier = %s',
            (user['tier'],),
            fetchone=True
        )
        
        # Family stats
        family_stats = execute_query('''
            SELECT COUNT(*) as family_members,
                   SUM(u.balance) as family_balance
            FROM family_members f
            JOIN users u ON f.member_id = u.user_id
            WHERE f.owner_id = %s
        ''', (user_id,), fetchone=True)
        
        return {
            'plan': user['plan'],
            'tier': user['tier'],
            'total_spent': float(user['total_spent'] or 0),
            'total_earned': float(user['total_earned'] or 0),
            'balance': float(user['balance'] or 0),
            'referral_code': user['referral_code'],
            'joined_date': user['joined_at'],
            'monthly_transactions': user['monthly_transactions'] or 0,
            'monthly_listings': user['monthly_listings'] or 0,
            'referred_count': referral_stats['referred_count'] or 0 if referral_stats else 0,
            'referred_revenue': float(referral_stats['referred_revenue'] or 0) if referral_stats else 0,
            'total_payments': payment_stats['total_payments'] or 0 if payment_stats else 0,
            'total_verified': float(payment_stats['total_verified_amount'] or 0) if payment_stats else 0,
            'max_transactions': tier_limits['max_transactions'] if tier_limits else 10,
            'max_listings': tier_limits['max_listings'] if tier_limits else 5,
            'max_balance': float(tier_limits['max_balance'] or 10000) if tier_limits else 10000,
            'daily_limit': float(tier_limits['daily_limit'] or 5000) if tier_limits else 5000,
            'family_members': family_stats['family_members'] or 0 if family_stats else 0,
            'family_balance': float(family_stats['family_balance'] or 0) if family_stats else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}

def get_plan(user_id: int) -> str:
    """Get user's current plan"""
    try:
        user = execute_query('''
            SELECT plan, last_payment FROM users WHERE user_id = %s
        ''', (user_id,), fetchone=True)
        
        if not user:
            return 'basic'
        
        if user['last_payment']:
            last_payment = user['last_payment']
            if isinstance(last_payment, str):
                last_payment = datetime.fromisoformat(last_payment.replace('Z', '+00:00'))
            
            if datetime.now() - last_payment <= timedelta(days=30):
                return user['plan'] or 'basic'
        
        # Check if user has basic plan in database
        return user['plan'] or 'basic'
        
    except Exception as e:
        logger.error(f"Error getting plan: {e}")
        return 'basic'

def get_fee(user_id: int) -> float:
    """Get user's transaction fee"""
    plan = get_plan(user_id)
    return {"basic": 2.5, "advanced": 1.5, "pro": 0.8}[plan]

def create_payment_v2(user_id: int, username: str, plan: str, amount: float, campaign_code: str = None):
    """Create payment with campaign tracking"""
    try:
        reference_code = f"{plan.upper()}-{user_id}-{int(datetime.now().timestamp())}"
        expires_at = datetime.now() + timedelta(hours=24)
        
        execute_query('''
            INSERT INTO payments 
            (user_id, username, plan, amount, reference_code, expires_at, campaign_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, username, plan, amount, reference_code, expires_at, campaign_code), commit=True)
        
        # Log analytics
        execute_query('''
            INSERT INTO analytics (event_type, user_id, data)
            VALUES (%s, %s, %s)
        ''', ('payment_initiated', user_id, json.dumps({
            'plan': plan,
            'amount': amount,
            'campaign': campaign_code
        })), commit=True)
        
        logger.info(f"💰 V2 Payment created: {user_id} - {plan} - {amount} - Campaign: {campaign_code}")
        return reference_code
        
    except Exception as e:
        logger.error(f"Error creating payment V2: {e}")
        return None

def verify_payment_v2(user_id: int, admin_id: int, amount: float = None, plan: str = None):
    """Verify payment with referral rewards"""
    try:
        # Get pending payment
        payment = execute_query('''
            SELECT * FROM payments 
            WHERE user_id = %s AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,), fetchone=True)
        
        if not payment:
            return False, "No pending payment found"
        
        payment_id = payment['id']
        actual_plan = plan or payment['plan']
        actual_amount = float(amount or payment['amount'])
        campaign_code = payment['campaign_id']
        
        # Apply campaign discount if exists
        final_amount = actual_amount
        if campaign_code:
            campaign = execute_query('''
                SELECT * FROM campaigns 
                WHERE code = %s AND is_active = true 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''', (campaign_code,), fetchone=True)
            
            if campaign:
                if campaign['type'] == 'discount' and campaign['discount_percent']:
                    discount = actual_amount * (float(campaign['discount_percent']) / 100)
                    final_amount = actual_amount - discount
                elif campaign['type'] == 'discount' and campaign['discount_amount']:
                    final_amount = actual_amount - float(campaign['discount_amount'])
                
                # Update campaign usage
                execute_query('''
                    UPDATE campaigns SET used_count = used_count + 1 WHERE id = %s
                ''', (campaign['id'],), commit=True)
        
        # Update payment
        execute_query('''
            UPDATE payments 
            SET status = 'verified', 
                verified_by = %s, 
                verified_at = CURRENT_TIMESTAMP,
                plan = %s,
                amount = %s
            WHERE id = %s
        ''', (admin_id, actual_plan, final_amount, payment_id), commit=True)
        
        # Update user plan and tier
        new_tier = 'basic'
        if actual_plan == 'advanced':
            new_tier = 'advanced'
        elif actual_plan == 'pro':
            new_tier = 'pro'
        
        # Calculate expiry date (30 days from now)
        expiry_date = datetime.now() + timedelta(days=30)
        
        execute_query('''
            UPDATE users 
            SET plan = %s, 
                tier = %s,
                tier_expires_at = %s,
                total_spent = total_spent + %s,
                last_payment = CURRENT_TIMESTAMP,
                last_active = CURRENT_TIMESTAMP,
                monthly_transactions = 0,  -- Reset counters on upgrade
                monthly_listings = 0
            WHERE user_id = %s
        ''', (actual_plan, new_tier, expiry_date, final_amount, user_id), commit=True)
        
        # Log tier upgrade
        execute_query('''
            INSERT INTO analytics (event_type, user_id, data)
            VALUES (%s, %s, %s)
        ''', ('tier_upgrade', user_id, json.dumps({
            'from': 'basic',
            'to': new_tier,
            'plan': actual_plan,
            'amount': final_amount
        })), commit=True)
        
        # Check for referral and reward referrer
        referrer = execute_query('''
            SELECT referred_by FROM users WHERE user_id = %s
        ''', (user_id,), fetchone=True)
        
        if referrer and referrer['referred_by']:
            reward_amount = final_amount * 0.10  # 10% referral reward
            execute_query('''
                UPDATE users 
                SET total_earned = total_earned + %s,
                    balance = balance + %s
                WHERE user_id = %s
            ''', (reward_amount, reward_amount, referrer['referred_by']), commit=True)
            
            # Log referral reward
            execute_query('''
                INSERT INTO analytics (event_type, user_id, data)
                VALUES (%s, %s, %s)
            ''', ('referral_reward', referrer['referred_by'], json.dumps({
                'referred_user': user_id,
                'amount': reward_amount
            })), commit=True)
        
        # Log analytics
        execute_query('''
            INSERT INTO analytics (event_type, user_id, data)
            VALUES (%s, %s, %s)
        ''', ('payment_verified', user_id, json.dumps({
            'plan': actual_plan,
            'amount': final_amount,
            'original_amount': actual_amount,
            'campaign': campaign_code,
            'new_tier': new_tier
        })), commit=True)
        
        return True, f"Payment verified! User upgraded to {actual_plan.upper()}. Tier: {new_tier.upper()}. Final amount: {final_amount:.2f} ETB"
        
    except Exception as e:
        logger.error(f"Error verifying payment V2: {e}")
        return False, f"Error: {str(e)}"

# ======================
# BACKUP SYSTEM
# ======================
def create_backup_v2():
    """Create PostgreSQL backup"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_v2_{timestamp}.sql")
        
        # Extract database connection parameters
        import urllib.parse
        result = urllib.parse.urlparse(DATABASE_URL)
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', result.hostname,
            '-p', str(result.port),
            '-U', result.username,
            '-d', result.path[1:],  # Remove leading /
            '-f', backup_file
        ]
        
        # Set password in environment
        env = os.environ.copy()
        env['PGPASSWORD'] = result.password
        
        # Execute backup
        import subprocess
        subprocess.run(cmd, env=env, check=True)
        
        # Create metadata file
        metadata = {
            'timestamp': timestamp,
            'database': DATABASE_URL,postgresql://postgres:nkIgStTDGjbqHYarRAyheKsTOXwcHKpa@postgres.railway.internal:5432/railway,
            'backup_file': backup_file,
            'size': os.path.getsize(backup_file),
            'version': 'V2.10',
            'database_type': 'PostgreSQL'
        }
        
        metadata_file = backup_file.replace('.sql', '.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Keep only last 20 backups
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_v2_")])
        if len(backups) > 20:
            for old_backup in backups[:-20]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                # Remove corresponding metadata
                metadata_file = old_backup.replace('.sql', '.json')
                if os.path.exists(os.path.join(BACKUP_DIR, metadata_file)):
                    os.remove(os.path.join(BACKUP_DIR, metadata_file))
        
        return True, backup_file
        
    except Exception as e:
        return False, str(e)

# ======================
# COMMAND HANDLERS - MAIN MENU
# ======================
async def start_v2(update: Update, context):
    """Enhanced start command with referral tracking"""
    user = update.effective_user
    
    # Check for referral parameter
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        logger.info(f"📨 User {user.id} came via referral code: {referral_code}")
    
    # Create/update user with referral
    user_ref_code = create_or_update_user_v2(user.id, user.username, user.full_name, "bot")
    
    # Process referral if exists
    if referral_code and user_ref_code:
        try:
            # Find referrer
            referrer = execute_query('''
                SELECT user_id FROM users WHERE referral_code = %s
            ''', (referral_code,), fetchone=True)
            
            if referrer:
                # Update user with referrer
                execute_query('''
                    UPDATE users SET referred_by = %s WHERE user_id = %s
                ''', (referrer['user_id'], user.id), commit=True)
                
                # Log analytics
                execute_query('''
                    INSERT INTO analytics (event_type, user_id, data)
                    VALUES (%s, %s, %s)
                ''', ('referral_click', user.id, json.dumps({
                    'referrer': referrer['user_id'],
                    'code': referral_code
                })), commit=True)
                
                logger.info(f"🤝 Referral linked: {user.id} -> {referrer['user_id']}")
            
        except Exception as e:
            logger.error(f"Error processing referral: {e}")
    
    # Get user stats with tier
    stats = get_user_stats(user.id)
    plan = get_plan(user.id)
    fee = get_fee(user.id)
    user_tier = TierSystem.get_user_tier(user.id)
    
    # Welcome message based on referral
    welcome_msg = "Welcome"
    if referral_code:
        welcome_msg = "Welcome! You were referred by a friend 🎉"
    
    keyboard = [
        [InlineKeyboardButton(f"⭐ {user_tier.upper()} TIER", callback_data="mytier_command"),
         InlineKeyboardButton("🚀 UPGRADE TIER", callback_data="tiers")],
        [InlineKeyboardButton("💰 MY WALLET", callback_data="wallet"),
         InlineKeyboardButton("🤝 REFER & EARN", callback_data="referral")],
        [InlineKeyboardButton("💸 SEND MONEY", callback_data="send_v2"),
         InlineKeyboardButton("🛍️ MARKETPLACE", callback_data="market_v2")],
        [InlineKeyboardButton("🔧 FIND WORK", callback_data="jobs_v2"),
         InlineKeyboardButton("🏠 PROPERTIES", callback_data="property_v2")],
        [InlineKeyboardButton("📊 TIER ANALYTICS", callback_data="tier_analytics"),
         InlineKeyboardButton("🎁 TIER PROMOTIONS", callback_data="tier_promotions")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 FAMILY/TEAM", callback_data="family_team"),
         InlineKeyboardButton("🚀 BULK OPS", callback_data="bulk_operations")],
        [InlineKeyboardButton("📞 SUPPORT", url=f"https://t.me/{SUPPORT.replace('@', '')}"),
         InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")]
    ]
    
    text = f"""🌟 *{BOT_NAME} V2.10* 🇪🇹
*{BOT_SLOGAN} with Complete Tier System*

{welcome_msg} @{user.username}!

*Your Profile:*
🏷️ Tier: {user_tier.upper()} ({stats.get('monthly_transactions', 0)}/{stats.get('max_transactions', 10)} tx)
💸 Fee: {fee}%
💰 Balance: {stats.get('balance', 0):.0f} ETB
👥 Referred: {stats.get('referred_count', 0)} users
🎯 Earned: {stats.get('total_earned', 0):.0f} ETB

*Quick Actions:*
• Check tier limits with /mytier
• View tier analytics & recommendations
• Upgrade tier for more features
• Manage family/team (Advanced+)
• Use bulk operations (Pro)

*Ready to maximize your earnings?*"""
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tiers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all tier features"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🟢 BASIC (FREE)", callback_data="tier_basic")],
        [InlineKeyboardButton("🟡 ADVANCED (149 ETB)", callback_data="tier_advanced")],
        [InlineKeyboardButton("🔴 PRO (999 ETB)", callback_data="tier_pro")],
        [InlineKeyboardButton("📊 COMPARE ALL", callback_data="compare_tiers")],
        [InlineKeyboardButton("📈 TIER ANALYTICS", callback_data="tier_analytics")],
        [InlineKeyboardButton("🤖 GET RECOMMENDATION", callback_data="tier_recommendation")],
        [InlineKeyboardButton("🔙 MAIN MENU", callback_data="back_to_main")]
    ]
    
    text = f"""🏆 *SHEGER ET V2.10 - COMPLETE TIERED SYSTEM*

*Your Current Tier:* {user_tier.upper()}

*Choose a tier to see detailed features:*
• 🟢 **BASIC** - Free forever
• 🟡 **ADVANCED** - For growing businesses
• 🔴 **PRO** - For enterprises

*Each tier unlocks more features in:*
✅ Payment System
✅ Marketplace
✅ Wallet System  
✅ Referral Program
✅ Family/Team Management
✅ Bulk Operations
✅ Analytics Dashboard
✅ API Access
✅ Campaigns
✅ Notifications

*Select a tier below for details:*"""
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mytier_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current tier and limits"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    tier_data = TierSystem.TIERS[user_tier]
    stats = get_user_stats(user_id)
    
    # Calculate usage percentages
    tx_percentage = (stats.get('monthly_transactions', 0) / max(stats.get('max_transactions', 1), 1)) * 100
    listing_percentage = (stats.get('monthly_listings', 0) / max(stats.get('max_listings', 1), 1)) * 100
    
    # Create usage bars
    tx_bar = "█" * min(10, int(tx_percentage / 10)) + "░" * (10 - min(10, int(tx_percentage / 10)))
    listing_bar = "█" * min(10, int(listing_percentage / 10)) + "░" * (10 - min(10, int(listing_percentage / 10)))
    
    keyboard = [
        [InlineKeyboardButton("📈 TIER ANALYTICS", callback_data="tier_analytics")],
        [InlineKeyboardButton("📊 USAGE TRENDS", callback_data="tier_trends")],
        [InlineKeyboardButton("🤖 AI RECOMMENDATION", callback_data="tier_recommendation")]
    ]
    
    if user_tier == 'basic':
        keyboard.append([InlineKeyboardButton("🟡 UPGRADE TO ADVANCED", callback_data="tier_advanced")])
        keyboard.append([InlineKeyboardButton("🔴 UPGRADE TO PRO", callback_data="tier_pro")])
    elif user_tier == 'advanced':
        keyboard.append([InlineKeyboardButton("🔴 UPGRADE TO PRO", callback_data="tier_pro")])
        keyboard.append([InlineKeyboardButton("🟢 DOWNGRADE TO BASIC", callback_data="tier_basic")])
    else:
        keyboard.append([InlineKeyboardButton("🟡 DOWNGRADE TO ADVANCED", callback_data="tier_advanced")])
        keyboard.append([InlineKeyboardButton("🎯 TIER PROMOTIONS", callback_data="tier_promotions")])
    
    keyboard.append([InlineKeyboardButton("📊 COMPARE ALL TIERS", callback_data="compare_tiers")])
    keyboard.append([InlineKeyboardButton("🔙 MAIN MENU", callback_data="back_to_main")])
    
    text = f"""⭐ *YOUR CURRENT TIER: {user_tier.upper()}*

*Status:* Active ✅
*Price:* {'FREE' if tier_data['price'] == 0 else f"{tier_data['price']} ETB/month"}
*Support:* {tier_data['support']}
*Uptime:* {tier_data['uptime']}
*Fee:* {tier_data['fee']}%

*Monthly Usage:*
💸 Transactions: {stats.get('monthly_transactions', 0)}/{stats.get('max_transactions', 10)}
{tx_bar} {tx_percentage:.0f}%
🛍️ Listings: {stats.get('monthly_listings', 0)}/{stats.get('max_listings', 5)}
{listing_bar} {listing_percentage:.0f}%

*Current Limits:*
💰 Wallet Balance: {stats.get('max_balance', 10000):,.0f} ETB max
📈 Daily Limit: {stats.get('daily_limit', 5000):,.0f} ETB
👨‍👩‍👧‍👦 Family Members: {tier_data['max_family_members']}
🚀 Bulk Operations: {'✅ Yes' if tier_data['bulk_operations'] else '❌ No'}
🔌 API Access: {'✅ Yes' if tier_data['api_access'] else '❌ No'}
💎 Commission Rate: {tier_data['commission_rate']}%

*Days until reset:* {(30 - datetime.now().day)} days

*Manage your tier below:*"""
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def premium_v2(update: Update, context):
    """Enhanced premium command with campaigns"""
    # Get active campaigns
    campaigns = execute_query('''
        SELECT name, code, discount_percent, discount_amount 
        FROM campaigns 
        WHERE type = 'discount' AND is_active = true
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ORDER BY created_at DESC LIMIT 3
    ''', fetchall=True)
    
    keyboard = [
        [InlineKeyboardButton("🚀 ADVANCED - 149 ETB/month", callback_data="upgrade_pro_v2")],
        [InlineKeyboardButton("🏢 PRO - 999 ETB/month", callback_data="upgrade_business_v2")],
        [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo")],
        [InlineKeyboardButton("📊 COMPARE TIERS", callback_data="compare_tiers")],
        [InlineKeyboardButton("🤖 AI RECOMMENDATION", callback_data="tier_recommendation")],
        [InlineKeyboardButton("🔙 MAIN MENU", callback_data="back_to_main")]
    ]
    
    if campaigns:
        keyboard.insert(0, [InlineKeyboardButton(f"🎯 {campaigns[0]['name']}", callback_data=f"campaign_{campaigns[0]['code']}")])
    
    text = f"""🚀 *{BOT_NAME} PREMIUM V2*

*Special Offers:*
"""
    
    for campaign in campaigns:
        if campaign['discount_percent']:
            text += f"• {campaign['name']}: {campaign['discount_percent']:.0f}% OFF (Code: {campaign['code']})\n"
        elif campaign['discount_amount']:
            text += f"• {campaign['name']}: {campaign['discount_amount']:.0f} ETB OFF\n"
    
    text += f"""
*1. SHEGER ADVANCED* - 149 ETB/month
• Fee: 1.5% (Basic: 2.5%) - Save 40%!
• Unlimited listings
• Priority support
• Business badge
• 50K ETB daily limit
• Referral earnings
• Up to 5 family members
• Basic analytics

*2. SHEGER PRO* - 999 ETB/month
• Fee: 0.8% (Lowest in Ethiopia!)
• Bulk payments API
• Business dashboard
• Dedicated manager
• White-label solutions
• Highest referral rates
• Unlimited family/team
• Advanced analytics
• API access
• Bulk operations

*💎 VIP Benefits:*
• Early access to new features
• Custom integration support
• Volume discounts
• Marketing co-promotion
• Priority feature requests

*Choose your plan and start saving today!*"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# BUTTON HANDLER - COMPLETE V2
# ======================
async def button_handler_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # ======================
    # TIER LIMIT CHECKS
    # ======================
    if query.data in ["upgrade_pro_v2", "upgrade_business_v2", "send_v2"]:
        check = TierSystem.check_limit(user_id, 'payment')
        if not check['allowed']:
            keyboard = [
                [InlineKeyboardButton(f"🚀 UPGRADE TO {check['upgrade'].upper()}", 
                                    callback_data=f"tier_{check['upgrade']}")],
                [InlineKeyboardButton("📊 SEE TIERS", callback_data="tiers")]
            ]
            
            await query.edit_message_text(
                f"⛔ *TIER LIMIT REACHED*\n\n{check['reason']}\n\n"
                "Upgrade to continue!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # ======================
    # HANDLE BUTTON CLICKS
    # ======================
    user = query.from_user
    username = user.username or f"user_{user_id}"
    
    if query.data == "back_to_main":
        await start_v2(update, context)
        return
    
    elif query.data == "tiers":
        await tiers_command(update, context)
        return
    
    elif query.data == "mytier_command":
        await mytier_command(update, context)
        return
    
    elif query.data == "premium_v2":
        await premium_v2(update, context)
        return
    
    elif query.data == "upgrade_pro_v2":
        # Create payment with campaign check
        reference_code = create_payment_v2(user_id, username, "advanced", 149)
        
        keyboard = [
            [InlineKeyboardButton("🎁 APPLY PROMO CODE", callback_data="apply_promo_pro")],
            [InlineKeyboardButton("💳 PAY NOW", callback_data=f"pay_now_{reference_code}")],
            [InlineKeyboardButton("🔙 BACK", callback_data="premium_v2")]
        ]
        
        text = f"""✅ *SHEGER ADVANCED SELECTED*

💰 *149 ETB/month*
👤 User: @{username}
🆔 Your ID: `{user_id}`
📋 Reference: `{reference_code}`

*Special Offers Available:*
• First month FREE with code: SHEGERLAUNCH
• Referral discount: REFER10
• Limited time promotions!

*Payment Instructions:*
1. Send *149 ETB* to:
   • telebirr: `{TELEBIRR}`
   • CBE Bank: `{CBE}`

2. Forward payment receipt to: {PAYMENTS}
   *IMPORTANT:* Include this code: `{reference_code}`

3. We'll activate your account within 30 minutes!

*Choose payment method:*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "upgrade_business_v2":
        reference_code = create_payment_v2(user_id, username, "pro", 999)
        
        text = f"""🏢 *SHEGER PRO SELECTED*

💰 *999 ETB/month*
👤 User: @{username}
🆔 Your ID: `{user_id}`
📋 Reference: `{reference_code}`

*For business inquiries, contact:* {SALES}

*Or send payment to:*
• telebirr: `{TELEBIRR}`
• CBE: `{CBE}`

*Include reference:* `{reference_code}`

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
    
    elif query.data == "compare_tiers":
        text = """📊 *COMPLETE TIER COMPARISON TABLE*

| Feature | 🟢 BASIC (FREE) | 🟡 ADVANCED (149 ETB) | 🔴 PRO (999 ETB) |
|---------|----------------|----------------------|-----------------|
| **💸 PAYMENTS** | | | |
| Monthly Tx | 10 | 100 | Unlimited |
| Fee | 2.5% | 1.5% | 0.8% |
| Daily Limit | 5,000 ETB | 50,000 ETB | 500,000 ETB |
| Methods | telebirr | +CBE, Bank | +Cards, Intl |
| Verification | 24-48h | 6-12h | Instant AI |
| Withdrawal Fee | 1% | 0.5% | 0.1% |
| **🛍️ MARKETPLACE** | | | |
| Listings | 5 | 50 | Unlimited |
| Images | 3 | 10 | 20 + Videos |
| Duration | 15 days | 30 days | 90 days |
| Analytics | Views only | +Contacts | Full Dashboard |
| Placement | Standard | Featured | Priority |
| **👨‍👩‍👧‍👦 FAMILY/TEAM** | | | |
| Max Members | 0 | 5 | Unlimited |
| Roles | None | Basic | Advanced |
| Shared Wallet | No | Yes | Yes |
| Spending Limits | No | Yes | Custom |
| **🚀 BULK OPS** | | | |
| Bulk Payments | No | No | Yes |
| CSV Import/Export | No | No | Yes |
| API Access | No | No | Yes |
| Batch Processing | No | No | Yes |
| **📊 ANALYTICS** | | | |
| Basic Analytics | ✅ | ✅ | ✅ |
| Advanced Analytics | ❌ | ✅ | ✅ |
| AI Recommendations | ❌ | ❌ | ✅ |
| Custom Reports | ❌ | ❌ | ✅ |
| **🎯 REFERRAL** | | | |
| Commission | 10% | 12% | 15% |
| Levels | 1 | 2 | 3 |
| Payout | Monthly | Weekly | Daily |
| **📞 SUPPORT** | | | |
| Support | Community | Priority Email | 24/7 Phone |
| Response Time | 48h | 12h | Instant |
| Dedicated Manager | No | No | Yes |
| **🔧 TECH** | | | |
| Storage | Local SQLite | Cloud SQLite | PostgreSQL Cloud |
| Uptime | 99% | 99.5% | 99.9% |
| Backup | Manual | Auto Weekly | Real-time Cloud |
| API | None | Read-only | Full Management |

*Ready to upgrade? Use /tiers to see plans!*"""
        
        keyboard = [
            [InlineKeyboardButton("🟢 BASIC DETAILS", callback_data="tier_basic")],
            [InlineKeyboardButton("🟡 ADVANCED DETAILS", callback_data="tier_advanced")],
            [InlineKeyboardButton("🔴 PRO DETAILS", callback_data="tier_pro")],
            [InlineKeyboardButton("💳 UPGRADE NOW", callback_data="premium_v2")],
            [InlineKeyboardButton("🤖 GET RECOMMENDATION", callback_data="tier_recommendation")],
            [InlineKeyboardButton("🔙 BACK", callback_data="tiers")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif query.data in ["tier_basic", "tier_advanced", "tier_pro"]:
        tier = query.data.replace("tier_", "")
        tier_data = TierSystem.TIERS[tier]
        
        if tier == 'basic':
            features = [
                '💸 **10 transactions/month** (2.5% fee)',
                '🛍️ **5 marketplace listings** (3 images each)',
                '💰 **10,000 ETB wallet limit** (1% withdrawal fee)',
                '🤝 **10% referral commission** (1 level)',
                '📊 **Basic analytics dashboard**',
                '👥 **Community support**',
                '🆓 **FREE forever**'
            ]
        elif tier == 'advanced':
            features = [
                '💸 **100 transactions/month** (1.5% fee - Save 40%!)',
                '🛍️ **50 marketplace listings** (10 images each)',
                '💰 **100,000 ETB wallet limit** (0.5% withdrawal fee)',
                '🤝 **12% referral commission** (2 levels)',
                '📊 **Advanced analytics dashboard**',
                '📧 **Priority email support**',
                '👨‍👩‍👧‍👦 **Family/Team management (5 members)**',
                '🚀 **Featured marketplace placement**'
            ]
        else:  # pro
            features = [
                '💸 **Unlimited transactions** (0.8% fee - Lowest!)',
                '🛍️ **Unlimited listings** (20 images + videos)',
                '💰 **Unlimited wallet** (0.1% withdrawal fee)',
                '🤝 **15% referral + 3 levels**',
                '📊 **Enterprise analytics + AI**',
                '📞 **24/7 phone + dedicated support**',
                '👨‍👩‍👧‍👦 **Unlimited family/team management**',
                '🚀 **Bulk operations & API access**',
                '🏢 **White-label solutions available**'
            ]
        
        text = f"""{tier_data['color']} *{tier.upper()} TIER*

*Price:* {'FREE' if tier_data['price'] == 0 else f"{tier_data['price']} ETB/month"}
*Max Users:* {tier_data['max_users']}
*Storage:* {tier_data['storage']}
*Support:* {tier_data['support']}
*Uptime:* {tier_data['uptime']}
*Family Members:* {tier_data['max_family_members']}
*Bulk Operations:* {'✅ Yes' if tier_data['bulk_operations'] else '❌ No'}
*API Access:* {'✅ Yes' if tier_data['api_access'] else '❌ No'}

*Key Features:*
{chr(10).join(['• ' + f for f in features])}

*Ready to upgrade? Click below!*"""
        
        keyboard = [
            [InlineKeyboardButton(f"💳 UPGRADE TO {tier.upper()}", callback_data=f"upgrade_{'pro' if tier == 'advanced' else 'business'}_v2")],
            [InlineKeyboardButton("📊 COMPARE ALL TIERS", callback_data="compare_tiers")],
            [InlineKeyboardButton("🎯 SEE PROMOTIONS", callback_data="tier_promotions")],
            [InlineKeyboardButton("🔙 BACK", callback_data="tiers")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif query.data == "wallet":
        await wallet_command(update, context)
        return
    
    elif query.data == "referral":
        await referral_system(update, context)
        return
    
    elif query.data == "send_v2":
        plan = get_plan(user_id)
        fee = get_fee(user_id)
        
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]]
        
        text = f"""💸 *SEND MONEY WITH {BOT_NAME} V2*

*Your current fee:* {fee}% ({plan.upper()} plan)

*Features:*
• Send to any phone number
• Bank transfers
• Instant to SHEGER users
• Scheduled payments
• Bulk payments (Pro only)

*Current Rates:*
• Basic: 2.5% (min 5 ETB)
• Advanced: 1.5% (Save 40%!)
• Pro: 0.8% (Lowest!)

*Daily Limits:*
• Basic: 5,000 ETB
• Advanced: 50,000 ETB
• Pro: 500,000 ETB

*Coming Soon:*
• International transfers
• Currency exchange
• Payment links
• QR code payments

*Upgrade now to save on fees!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "market_v2":
        plan = get_plan(user_id)
        user_tier = TierSystem.get_user_tier(user_id)
        
        listings = "Unlimited listings" if user_tier != 'basic' else "5 free listings/month"
        placement = "Priority placement" if user_tier != 'basic' else "Standard placement"
        analytics = "Advanced analytics" if user_tier == 'pro' else "Basic analytics"
        
        keyboard = [
            [InlineKeyboardButton("🛒 BROWSE LISTINGS", callback_data="browse_market")],
            [InlineKeyboardButton("➕ CREATE LISTING", callback_data="create_listing")],
            [InlineKeyboardButton("📊 MY LISTINGS", callback_data="my_listings")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🛍️ *{BOT_NAME} MARKETPLACE V2*

*Your Tier ({user_tier.upper()}):*
• {listings}
• {placement}
• {analytics}
• {"Escrow protection" if user_tier != 'basic' else "Basic protection"}
• {"Unlimited images" if user_tier == 'pro' else "Limited images"}

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

*Start buying or selling today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "jobs_v2":
        keyboard = [
            [InlineKeyboardButton("🔍 SEARCH JOBS", callback_data="search_jobs")],
            [InlineKeyboardButton("➕ POST JOB", callback_data="post_job")],
            [InlineKeyboardButton("📊 MY APPLICATIONS", callback_data="my_applications")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🔧 *FIND WORK ON {BOT_NAME} V2*

*Top Job Categories:*
• 💻 Tech & Programming (150+ jobs)
• 🏗️ Construction & Labor (80+ jobs)
• 🚚 Driving & Delivery (120+ jobs)
• 👨‍🏫 Teaching & Tutoring (60+ jobs)
• 🏥 Healthcare (45+ jobs)
• 🍽️ Hospitality (75+ jobs)
• 📊 Administration (90+ jobs)

*For Job Seekers:*
• Browse thousands of verified jobs
• Apply directly through bot
• Get instant job alerts
• Build professional profile
• Secure escrow payments

*For Employers:*
• Post jobs for FREE
• Reach qualified candidates
• Manage applications easily
• Hire with confidence
• Rating system

*Start your job search or post a job today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "property_v2":
        keyboard = [
            [InlineKeyboardButton("🔍 SEARCH PROPERTIES", callback_data="search_properties")],
            [InlineKeyboardButton("➕ LIST PROPERTY", callback_data="list_property")],
            [InlineKeyboardButton("📊 MY LISTINGS", callback_data="my_properties")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
        ]
        
        text = f"""🏠 *PROPERTIES ON {BOT_NAME} V2*

*Find Your Perfect Property:*
• 🏡 Houses for Rent/Sale
• 🏢 Apartments & Condos
• 🏪 Commercial Spaces
• 🗺️ Land & Plots
• 🏖️ Vacation Rentals
• 🏨 Hotel & Guest Houses

*Verified Properties Only:*
✅ All listings verified
✅ Authentic photos
✅ Accurate location data
✅ Price transparency
✅ Owner/Agent verification

*Advanced Features:*
• Virtual tours
• Mortgage calculator
• Price alerts
• Save favorites
• Neighborhood info

*Find your dream home or investment property today!*"""
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "tier_analytics":
        await tier_analytics_dashboard(update, context)
        return
    
    elif query.data == "tier_recommendation":
        await tier_recommendation_engine(update, context)
        return
    
    elif query.data == "tier_promotions":
        await tier_promotions_special(update, context)
        return
    
    elif query.data == "family_team":
        await tier_family_team(update, context)
        return
    
    elif query.data == "bulk_operations":
        await tier_bulk_operations(update, context)
        return
    
    elif query.data == "settings":
        await settings_menu(update, context)
        return
    
    else:
        # Handle other buttons
        await query.edit_message_text(
            f"🔄 Feature coming soon!\n\nButton: {query.data}\n\nUse /start to return to main menu.",
            parse_mode='Markdown'
        )

# ======================
# TIER ANALYTICS FUNCTIONS
# ======================
async def tier_analytics_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed tier analytics for users"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    result = execute_query('''
        SELECT 
            u.monthly_transactions,
            u.monthly_listings,
            tl.max_transactions,
            tl.max_listings,
            tl.max_balance,
            tl.daily_limit
        FROM users u
        LEFT JOIN tier_limits tl ON u.tier = tl.tier
        WHERE u.user_id = %s
    ''', (user_id,), fetchone=True)
    
    if not result:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Could not fetch tier analytics.")
        else:
            await update.message.reply_text("❌ Could not fetch tier analytics.")
        return
    
    # Calculate usage percentages
    tx_percentage = (result['monthly_transactions'] / max(result['max_transactions'], 1)) * 100
    listing_percentage = (result['monthly_listings'] / max(result['max_listings'], 1)) * 100
    
    # Create visual bars
    tx_bar = "█" * min(10, int(tx_percentage / 10)) + "░" * (10 - min(10, int(tx_percentage / 10)))
    listing_bar = "█" * min(10, int(listing_percentage / 10)) + "░" * (10 - min(10, int(listing_percentage / 10)))
    
    # Calculate potential savings
    basic_fee = 2.5
    advanced_fee = 1.5
    pro_fee = 0.8
    
    current_tier_fee = {
        'basic': basic_fee,
        'advanced': advanced_fee,
        'pro': pro_fee
    }.get(user_tier, basic_fee)
    
    typical_monthly_tx = 10000  # Example monthly transaction volume
    current_cost = typical_monthly_tx * (current_tier_fee / 100)
    
    potential_savings = {}
    if user_tier == 'basic':
        advanced_cost = typical_monthly_tx * (advanced_fee / 100)
        pro_cost = typical_monthly_tx * (pro_fee / 100)
        potential_savings['advanced'] = current_cost - advanced_cost
        potential_savings['pro'] = current_cost - pro_cost
    elif user_tier == 'advanced':
        pro_cost = typical_monthly_tx * (pro_fee / 100)
        potential_savings['pro'] = current_cost - pro_cost
    
    keyboard = [
        [InlineKeyboardButton("📈 USAGE TRENDS", callback_data="tier_trends")],
        [InlineKeyboardButton("💰 COST ANALYSIS", callback_data="cost_optimization")],
        [InlineKeyboardButton("📊 TIER COMPARISON", callback_data="compare_tiers")],
        [InlineKeyboardButton("🚀 UPGRADE RECOMMENDATION", callback_data="tier_recommendation")],
        [InlineKeyboardButton("🔙 BACK", callback_data="mytier_command")]
    ]
    
    text = f"""📊 *TIER ANALYTICS DASHBOARD*

*Current Tier:* {user_tier.upper()}

*Usage This Month:*
💸 Transactions: {result['monthly_transactions']}/{result['max_transactions']}
{tx_bar} {tx_percentage:.0f}%
🛍️ Listings: {result['monthly_listings']}/{result['max_listings']}
{listing_bar} {listing_percentage:.0f}%

*Monthly Limits:*
💰 Wallet Balance: {float(result['max_balance'] or 10000):,.0f} ETB max
📈 Daily Limit: {float(result['daily_limit'] or 5000):,.0f} ETB

*Estimated Monthly Costs:*
🎯 Based on 10,000 ETB monthly volume:
• Your Tier ({user_tier.upper()}): {current_cost:,.0f} ETB"""
    
    if potential_savings:
        if 'advanced' in potential_savings:
            text += f"\n• Advanced: {typical_monthly_tx * (advanced_fee/100):,.0f} ETB (Save {potential_savings['advanced']:,.0f} ETB!)"
        if 'pro' in potential_savings:
            text += f"\n• Pro: {typical_monthly_tx * (pro_fee/100):,.0f} ETB (Save {potential_savings['pro']:,.0f} ETB!)"
    
    text += f"""

*Recommendation:* """
    
    if tx_percentage > 80 or listing_percentage > 80:
        next_tier = 'pro' if user_tier == 'advanced' else 'advanced'
        text += f"Consider upgrading to {next_tier.upper()}! You're using {max(tx_percentage, listing_percentage):.0f}% of your limits."
    elif tx_percentage < 30 and listing_percentage < 30:
        text += "Your current tier fits your usage well."
    else:
        text += "Monitor your usage. Upgrade if you expect more activity."
    
    text += f"""

*Days until reset:* {(30 - datetime.now().day)} days

*Check detailed analytics below:*"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tier_recommendation_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-powered tier recommendation based on user behavior"""
    user_id = update.effective_user.id
    
    # Analyze user behavior
    user_data = execute_query('''
        SELECT 
            COUNT(p.id) as total_payments,
            SUM(p.amount) as total_spent,
            u.monthly_transactions,
            u.monthly_listings,
            u.tier
        FROM users u
        LEFT JOIN payments p ON u.user_id = p.user_id AND p.status = 'verified'
        WHERE u.user_id = %s
        GROUP BY u.user_id
    ''', (user_id,), fetchone=True)
    
    if not user_data:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Could not analyze your usage data.")
        else:
            await update.message.reply_text("❌ Could not analyze your usage data.")
        return
    
    # Calculate usage scores (0-100)
    tx_usage = (user_data['monthly_transactions'] / 10) * 100  # Based on basic tier
    listing_usage = (user_data['monthly_listings'] / 5) * 100   # Based on basic tier
    
    # Determine recommendation
    current_tier = user_data['tier']
    recommendation = current_tier
    reasons = []
    
    if current_tier == 'basic':
        if tx_usage > 70 or listing_usage > 70:
            recommendation = 'advanced'
            reasons.append(f"High usage ({tx_usage:.0f}% transactions, {listing_usage:.0f}% listings)")
        
        if user_data['total_spent'] and float(user_data['total_spent']) > 50000:
            recommendation = 'advanced'
            reasons.append(f"High spending ({float(user_data['total_spent']):,.0f} ETB total)")
    
    elif current_tier == 'advanced':
        if tx_usage > 70 or listing_usage > 70:
            recommendation = 'pro'
            reasons.append(f"High usage ({tx_usage:.0f}% transactions, {listing_usage:.0f}% listings)")
        
        if user_data['total_spent'] and float(user_data['total_spent']) > 200000:
            recommendation = 'pro'
            reasons.append(f"High spending ({float(user_data['total_spent']):,.0f} ETB total)")
    
    # Calculate cost-benefit analysis
    monthly_volume = float(user_data['total_spent'] or 0) / 12 if user_data['total_spent'] else 10000
    current_fee = {'basic': 2.5, 'advanced': 1.5, 'pro': 0.8}[current_tier]
    recommended_fee = {'basic': 2.5, 'advanced': 1.5, 'pro': 0.8}[recommendation]
    
    current_cost = monthly_volume * (current_fee / 100)
    recommended_cost = monthly_volume * (recommended_fee / 100)
    monthly_savings = current_cost - recommended_cost
    
    keyboard = [
        [InlineKeyboardButton(f"💳 UPGRADE TO {recommendation.upper()}", callback_data=f"upgrade_{'pro' if recommendation == 'advanced' else 'business'}_v2")],
        [InlineKeyboardButton("📊 COMPARE ALL TIERS", callback_data="compare_tiers")],
        [InlineKeyboardButton("📈 VIEW ANALYTICS", callback_data="tier_analytics")],
        [InlineKeyboardButton("🔙 BACK", callback_data="mytier_command")]
    ]
    
    text = f"""🤖 *AI-POWERED TIER RECOMMENDATION*

*Analysis Results:*
📊 Current Tier: {current_tier.upper()}
🎯 Recommended: {recommendation.upper()}

*Your Usage Pattern:*
💸 Monthly Transactions: {user_data['monthly_transactions']}
🛍️ Monthly Listings: {user_data['monthly_listings']}
💰 Total Spent: {float(user_data['total_spent'] or 0):,.0f} ETB

*Why {recommendation.upper()}?*"""
    
    if reasons:
        for i, reason in enumerate(reasons, 1):
            text += f"\n{i}. {reason}"
    else:
        text += "\n• Your current tier fits your usage pattern well"
    
    text += f"""

*Financial Impact:*
💵 Estimated Monthly Volume: {monthly_volume:,.0f} ETB
📉 Current Fee: {current_fee}% = {current_cost:,.0f} ETB/month
📈 {recommendation.upper()} Fee: {recommended_fee}% = {recommended_cost:,.0f} ETB/month"
    
    if recommendation != current_tier:
        text += f"\n💰 *Monthly Savings:* {monthly_savings:,.0f} ETB"
        text += f"\n🏆 *Annual Savings:* {monthly_savings * 12:,.0f} ETB"
    
    text += f"""

*Additional Benefits:*
• Higher transaction limits
• More marketplace listings
• Better referral commissions
• Priority support
• Advanced analytics"""

    if recommendation == 'pro':
        text += "\n• Dedicated account manager"
        text += "\n• API access"
        text += "\n• Bulk processing"
    
    text += f"""

*Ready to optimize? Upgrade now!*"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User wallet dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    user_tier = TierSystem.get_user_tier(user.id)
    
    # Tier-based withdrawal fees
    withdrawal_fees = {'basic': 1.0, 'advanced': 0.5, 'pro': 0.1}
    withdrawal_fee = withdrawal_fees.get(user_tier, 1.0)
    
    keyboard = [
        [InlineKeyboardButton("📥 ADD FUNDS", callback_data="add_funds"),
         InlineKeyboardButton("📤 WITHDRAW", callback_data="withdraw_funds")],
        [InlineKeyboardButton("📋 TRANSACTION HISTORY", callback_data="transactions")],
        [InlineKeyboardButton("💰 FAMILY WALLET", callback_data="family_wallet"),
         InlineKeyboardButton("📊 WALLET ANALYTICS", callback_data="wallet_analytics")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""💰 *YOUR SHEGER WALLET*

*Tier:* {user_tier.upper()}
*Withdrawal Fee:* {withdrawal_fee}%

*Balance Summary:*
💳 Available Balance: {stats.get('balance', 0):.0f} ETB
📈 Total Earned: {stats.get('total_earned', 0):.0f} ETB
💸 Total Spent: {stats.get('total_spent', 0):.0f} ETB
🏦 Max Balance Limit: {stats.get('max_balance', 10000):,.0f} ETB
👨‍👩‍👧‍👦 Family Balance: {stats.get('family_balance', 0):,.0f} ETB

*Withdrawal Info:*
• Min: 100 ETB
• Fee: {withdrawal_fee}%
• Time: {'Instant' if user_tier == 'pro' else '24 hours'}
• Methods: telebirr, CBE

*Upgrade to Pro for instant withdrawals!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def referral_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced referral system"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    user_tier = TierSystem.get_user_tier(user.id)
    
    # Tier-based commission rates
    commission_rates = {'basic': 10, 'advanced': 12, 'pro': 15}
    commission = commission_rates.get(user_tier, 10)
    
    referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={stats['referral_code']}"
    
    keyboard = [
        [InlineKeyboardButton("📋 COPY REFERRAL LINK", callback_data="copy_ref_link")],
        [InlineKeyboardButton("👥 MY REFERRALS", callback_data="my_referrals")],
        [InlineKeyboardButton("💰 WITHDRAW EARNINGS", callback_data="withdraw")],
        [InlineKeyboardButton("📊 REFERRAL ANALYTICS", callback_data="referral_analytics")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""🤝 *REFER & EARN PROGRAM*

*Your Tier:* {user_tier.upper()}
*Your Commission Rate:* {commission}%

*Your Referral Stats:*
👥 Total Referred: {stats.get('referred_count', 0)} users
💰 Total Earned: {stats.get('total_earned', 0):.0f} ETB
💳 Available Balance: {stats.get('balance', 0):.0f} ETB
🎯 Lifetime Potential: Unlimited!

*How It Works:*
1. Share your unique link below
2. Friends sign up using your link
3. When they upgrade to ADVANCED/PRO
4. You earn *{commission}% commission* instantly!

*Your Unique Link:*
`{referral_link}`

*Your Referral Code:*
`{stats['referral_code']}`

*Commission Rates by Tier:*
• Basic: 10% commission
• Advanced: 12% commission (+20% bonus!)
• Pro: 15% commission (+50% bonus!)

*Earnings Example:*
• ADVANCED upgrade (149 ETB) → You earn {149 * (commission/100):.1f} ETB
• PRO upgrade (999 ETB) → You earn {999 * (commission/100):.1f} ETB
• Lifetime earnings on their renewals!

*Start sharing and earning today!*"""
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tier_family_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Family/team management for Advanced+ tiers"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    if user_tier == 'basic':
        keyboard = [
            [InlineKeyboardButton("🟡 UPGRADE TO ADVANCED", callback_data="tier_advanced")],
            [InlineKeyboardButton("📊 SEE TIER FEATURES", callback_data="compare_tiers")]
        ]
        
        text = f"""👨‍👩‍👧‍👦 *FAMILY/TEAM FEATURES*

*Available in ADVANCED and PRO tiers only.*

*Your current tier:* {user_tier.upper()}

*Family/Team Benefits:*
• Share wallet with family
• Manage team permissions
• Set spending limits
• Track team activity
• Combined reporting

*ADVANCED Tier (149 ETB/month):*
• Up to 5 family members
• Basic permissions
• Shared balance view
• Spending notifications

*PRO Tier (999 ETB/month):*
• Unlimited team members
• Advanced permissions
• Role-based access
• Detailed analytics
• Custom limits per member

*Perfect for:*
🏠 Families sharing expenses
👨‍💼 Small business teams
🏢 Organizations with multiple users
👥 Groups managing funds together

*Upgrade now to start sharing!*"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ ADD MEMBER", callback_data="family_add")],
        [InlineKeyboardButton("👥 MANAGE MEMBERS", callback_data="family_manage")],
        [InlineKeyboardButton("💰 FAMILY WALLET", callback_data="family_wallet")],
        [InlineKeyboardButton("📊 FAMILY ANALYTICS", callback_data="family_analytics")],
        [InlineKeyboardButton("⚙️ SETTINGS", callback_data="family_settings")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""👨‍👩‍👧‍👦 *FAMILY/TEAM MANAGEMENT*

*Your Tier:* {user_tier.upper()}
*Member Limit:* {5 if user_tier == 'advanced' else 'Unlimited'} members

*Available Actions:*
• Add new family/team members
• Set spending limits per member
• Assign roles and permissions
• Monitor family spending
• View combined analytics

*Role Types:*
👑 **Owner** - Full control
👨‍💼 **Manager** - Can add members, set limits
👤 **Member** - Can spend within limits
👀 **Viewer** - View only, no spending

*Getting Started:*
1. Click ADD MEMBER
2. Enter user ID or username
3. Set role and limits
4. Send invitation
5. Start sharing!

*Need help managing your team?* Contact {SUPPORT}"""

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tier_bulk_operations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bulk operations for Pro tier users"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    if user_tier != 'pro':
        keyboard = [
            [InlineKeyboardButton("🚀 UPGRADE TO PRO", callback_data="tier_pro")],
            [InlineKeyboardButton("📊 SEE TIER FEATURES", callback_data="compare_tiers")]
        ]
        
        text = f"""⛔ *PRO TIER FEATURE ONLY*

*This feature is available only for PRO tier users.*

Your current tier: {user_tier.upper()}

*PRO Tier Benefits:*
• Bulk payment processing
• CSV import/export
• API access
• Batch operations
• Priority processing

*Upgrade to PRO to unlock:*
✅ Bulk send payments to 100+ users
✅ Import contacts from CSV
✅ Export transaction history
✅ Schedule recurring payments
✅ Advanced reporting

*Price:* 999 ETB/month
*Ready to scale your business?*"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    keyboard = [
        [InlineKeyboardButton("📤 BULK SEND PAYMENTS", callback_data="bulk_send")],
        [InlineKeyboardButton("📥 IMPORT CONTACTS", callback_data="bulk_import")],
        [InlineKeyboardButton("📋 EXPORT TRANSACTIONS", callback_data="bulk_export")],
        [InlineKeyboardButton("🔄 SCHEDULE RECURRING", callback_data="bulk_schedule")],
        [InlineKeyboardButton("📊 BATCH REPORTS", callback_data="bulk_reports")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""🚀 *PRO TIER - BULK OPERATIONS*

*Available Bulk Features:*

*1. 📤 Bulk Send Payments*
• Send to multiple recipients at once
• CSV file upload support
• Template-based payments
• Batch confirmation

*2. 📥 Import Contacts*
• Import from CSV/Excel
• Phone number validation
• Auto-categorization
• Duplicate detection

*3. 📋 Export Transactions*
• Export to CSV/Excel/PDF
• Custom date ranges
• Filter by type/status
• Automated reports

*4. 🔄 Schedule Recurring*
• Monthly salary payments
• Vendor payments
• Subscription collections
• Automated invoicing

*5. 📊 Batch Reports*
• Performance analytics
• Cost optimization
• Growth metrics
• ROI analysis

*How to Use:*
1. Select operation type
2. Upload file or enter data
3. Review and confirm
4. Track progress in dashboard

*Need help?* Contact {SUPPORT}"""

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def tier_promotions_special(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Special promotions for tier upgrades"""
    user_id = update.effective_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🎁 LAUNCH SPECIAL - 100% OFF", callback_data="promo_SHEGERLAUNCH")],
        [InlineKeyboardButton("🤝 REFERRAL BONUS - 10%", callback_data="promo_REFER10")],
        [InlineKeyboardButton("🚀 UPGRADE50 - 50% OFF", callback_data="promo_UPGRADE50")],
        [InlineKeyboardButton("📊 COMPARE ALL TIERS", callback_data="compare_tiers")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    text = f"""🎯 *TIER UPGRADE PROMOTIONS*

*Your Current Tier:* {user_tier.upper()}

*Active Promotions:*
• 🎁 *Launch Special*: First month FREE with code SHEGERLAUNCH
• 🤝 *Referral Bonus*: Get 14.9 ETB per referral with code REFER10
• 🚀 *First Upgrade*: 50% OFF your first upgrade with code UPGRADE50
• 💼 *Pro Bundle*: 30% OFF Pro upgrade with code PROBUNDLE

*How to Apply Promotions:*
1. Click on a promotion below
2. Copy the promo code
3. Click UPGRADE on tier page
4. Apply code during payment
5. Enjoy discounted rate!

*Terms & Conditions:*
• One promotion per user
• Cannot combine offers
• Valid for new upgrades only
• Limited time offers
• Admin reserves right to modify"""

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User settings menu"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_tier = TierSystem.get_user_tier(user_id)
    
    keyboard = [
        [InlineKeyboardButton("👤 PROFILE SETTINGS", callback_data="profile_settings"),
         InlineKeyboardButton("🔔 NOTIFICATIONS", callback_data="notification_settings")],
        [InlineKeyboardButton("🔒 PRIVACY", callback_data="privacy_settings"),
         InlineKeyboardButton("💳 PAYMENT METHODS", callback_data="payment_settings")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 FAMILY SETTINGS", callback_data="family_settings"),
         InlineKeyboardButton("📊 DATA & ANALYTICS", callback_data="data_settings")],
        [InlineKeyboardButton("🛡️ SECURITY", callback_data="security_settings"),
         InlineKeyboardButton("🌐 LANGUAGE", callback_data="language_settings")],
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_main")]
    ]
    
    # Only show advanced settings for Advanced+ tiers
    if user_tier != 'basic':
        keyboard.insert(2, [InlineKeyboardButton("⚙️ ADVANCED SETTINGS", callback_data="advanced_settings")])
    
    text = f"""⚙️ *SETTINGS*

*Current Tier:* {user_tier.upper()}

*Manage your account settings:*

• *Profile* - Update personal information
• *Notifications* - Control notification preferences
• *Privacy* - Manage privacy settings
• *Payment Methods* - Add/remove payment methods
• *Family/Team* - Manage family or team settings
• *Data & Analytics* - Data export and preferences
• *Security* - Security and login settings
• *Language* - Change language preference

*Need help with settings?* Contact {SUPPORT}"""

    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# ADMIN COMMANDS
# ======================
async def admin_dashboard(update: Update, context):
    """Admin dashboard"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Get statistics
    result = execute_query("SELECT COUNT(*) as count FROM users", fetchone=True)
    total_users = result['count'] if result else 0
    
    result = execute_query("SELECT COUNT(*) as count FROM users WHERE plan != 'basic'", fetchone=True)
    premium_users = result['count'] if result else 0
    
    result = execute_query("SELECT SUM(amount) as total FROM payments WHERE status = 'verified'", fetchone=True)
    total_revenue = float(result['total'] or 0) if result else 0
    
    result = execute_query("SELECT COUNT(*) as count FROM payments WHERE status = 'pending'", fetchone=True)
    pending_payments = result['count'] if result else 0
    
    # Tier statistics
    tier_stats = execute_query('''
        SELECT tier, COUNT(*) as count,
               SUM(balance) as total_balance,
               AVG(total_spent) as avg_spent
        FROM users
        GROUP BY tier
        ORDER BY tier
    ''', fetchall=True)
    
    text = f"""👑 *SHEGER ET ADMIN DASHBOARD V2.10*

*Platform Overview:*
👥 Total Users: {total_users:,}
💎 Premium Users: {premium_users} ({premium_users/max(total_users,1)*100:.1f}%)
💰 Total Revenue: {total_revenue:,.0f} ETB
⏳ Pending Payments: {pending_payments}

*Tier Statistics:*"""
    
    for tier in tier_stats:
        percentage = (tier['count'] / total_users * 100) if total_users > 0 else 0
        text += f"""
• {tier['tier'].upper()}: {tier['count']} users ({percentage:.1f}%)
  Avg Spent: {float(tier['avg_spent'] or 0):,.0f} ETB
  Total Balance: {float(tier['total_balance'] or 0):,.0f} ETB"""
    
    text += f"""
*Quick Commands:*
`/verify USER_ID` - Verify payment
`/pending` - View pending payments
`/revenue` - Revenue analytics
`/broadcast` - Send announcement
`/backup` - Create backup
`/tierstats` - Tier analytics

*Today's Priority:*
✅ Verify pending payments
✅ Check tier migration
✅ Monitor campaign performance
✅ Create backup
✅ Engage with users"""

    await update.message.reply_text(text, parse_mode='Markdown')

async def verify_payment_admin(update: Update, context):
    """Verify payment as admin"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /verify USER_ID [AMOUNT] [PLAN]")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1]) if len(context.args) > 1 else None
        plan = context.args[2] if len(context.args) > 2 else None
        
        success, message = verify_payment_v2(user_id, update.effective_user.id, amount, plan)
        
        if success:
            # Send notification to user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 *PAYMENT VERIFIED!*\n\nYour payment has been verified. You now have access to premium features!\n\n{message}",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Error: {e}\nUsage: /verify USER_ID [AMOUNT] [PLAN]")

async def pending_payments_admin(update: Update, context):
    """View pending payments"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Get pending payments
    pending = execute_query('''
        SELECT p.*, u.username, u.full_name, u.plan as user_plan, u.tier
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
        LIMIT 20
    ''', fetchall=True)
    
    if not pending:
        await update.message.reply_text("✅ No pending payments.")
        return
    
    text = f"⏳ *PENDING PAYMENTS - {len(pending)}*\n\n"
    
    for payment in pending:
        created = payment['created_at'].strftime('%b %d %H:%M')
        
        text += f"""• *ID:* `{payment['id']}`
   👤 User: @{payment['username'] or payment['user_id']}
   🏷️ Tier: {payment['tier']}
   💰 Amount: {float(payment['amount']):.0f} ETB
   📋 Plan: {payment['plan'].upper()}
   📎 Ref: `{payment['reference_code']}`
   🕐 Created: {created}
   
   `/verify {payment['user_id']} {payment['amount']} {payment['plan']}`
   
   """
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def revenue_admin(update: Update, context):
    """Revenue analytics"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    # Daily revenue for last 7 days
    daily_revenue = execute_query('''
        SELECT DATE(verified_at) as date,
               COUNT(*) as transactions,
               SUM(amount) as revenue,
               AVG(amount) as avg_ticket
        FROM payments 
        WHERE status = 'verified' 
        AND verified_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(verified_at)
        ORDER BY date DESC
    ''', fetchall=True)
    
    # Revenue by tier
    tier_revenue = execute_query('''
        SELECT u.tier,
               COUNT(p.id) as transactions,
               SUM(p.amount) as revenue,
               AVG(p.amount) as avg_ticket
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.status = 'verified'
        GROUP BY u.tier
        ORDER BY revenue DESC
    ''', fetchall=True)
    
    text = f"""📈 *REVENUE ANALYTICS*

*Last 7 Days Performance:*"""
    
    total_7day = 0
    for day in daily_revenue:
        date = day['date'].strftime('%b %d')
        text += f"\n• {date}: {float(day['revenue']):,.0f} ETB ({day['transactions']} tx)"
        total_7day += float(day['revenue'])
    
    text += f"\n*7-Day Total:* {total_7day:,.0f} ETB"
    text += f"\n*Daily Average:* {total_7day/len(daily_revenue) if daily_revenue else 0:,.0f} ETB"
    
    text += f"\n\n*Revenue by Tier:*"
    for tier in tier_revenue:
        text += f"\n• {tier['tier'].upper()}: {float(tier['revenue']):,.0f} ETB ({tier['transactions']} tx, Avg: {float(tier['avg_ticket']):,.0f} ETB)"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def backup_admin(update: Update, context):
    """Create backup"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    success, backup_file = create_backup_v2()
    
    if success:
        await update.message.reply_text(f"✅ Backup created: `{backup_file}`")
    else:
        await update.message.reply_text(f"❌ Backup failed: {backup_file}")

async def broadcast_admin(update: Update, context):
    """Broadcast message to users"""
    if update.effective_user.id != 7714584854:
        await update.message.reply_text("⛔ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast TIER MESSAGE\n\nTiers: all, basic, advanced, pro, premium")
        return
    
    tier_filter = context.args[0].lower()
    message = " ".join(context.args[1:])
    
    if not message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return
    
    if tier_filter == "all":
        users = execute_query("SELECT user_id FROM users WHERE status = 'active'", fetchall=True)
    elif tier_filter == "premium":
        users = execute_query("SELECT user_id FROM users WHERE plan != 'basic' AND status = 'active'", fetchall=True)
    else:
        users = execute_query("SELECT user_id FROM users WHERE tier = %s AND status = 'active'", (tier_filter,), fetchall=True)
    
    if not users:
        await update.message.reply_text(f"No users found for tier: {tier_filter}")
        return
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users ({tier_filter})...")
    
    successful = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *ANNOUNCEMENT FROM SHEGER ET*\n\n{message}\n\n_This is an automated message_",
                parse_mode='Markdown'
            )
            successful += 1
        except:
            failed += 1
        
        # Small delay to avoid rate limits
        await asyncio.sleep(0.1)
    
    await update.message.reply_text(f"✅ Broadcast complete!\n\n✅ Successful: {successful}\n❌ Failed: {failed}")

# ======================
# SCHEDULED TASKS
# ======================
async def scheduled_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Automated scheduled tasks"""
    try:
        logger.info("🔄 Running scheduled tasks...")
        
        # 1. Create daily backup
        success, backup_file = create_backup_v2()
        if success:
            logger.info(f"📦 Daily backup created: {backup_file}")
        
        # 2. Check for expired payments
        expired = execute_query('''
            SELECT p.*, u.username 
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending' 
            AND p.expires_at < CURRENT_TIMESTAMP
        ''', fetchall=True)
        
        for payment in expired:
            # Update status
            execute_query('UPDATE payments SET status = \'expired\' WHERE id = %s', (payment['id'],), commit=True)
        
        # 3. Reset monthly tier counters on 1st of each month
        if datetime.now().day == 1:
            TierSystem.reset_monthly_counters()
            logger.info("📅 Monthly tier counters reset")
        
        logger.info("✅ Scheduled tasks completed")
        
    except Exception as e:
        logger.error(f"Error in scheduled tasks: {e}")

# ======================
# MAIN FUNCTION
# ======================
def main():
    """Main application setup"""
    # Get bot token from environment
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not found!")
        print("Please set your bot token:")
        print("1. Get token from @BotFather on Telegram")
        print("2. Run: export TELEGRAM_TOKEN='your_token_here'")
        print("3. Or create a .env file with TELEGRAM_TOKEN=your_token")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # ======================
    # COMMAND HANDLERS
    # ======================
    
    # User commands
    application.add_handler(CommandHandler("start", start_v2))
    application.add_handler(CommandHandler("tiers", tiers_command))
    application.add_handler(CommandHandler("mytier", mytier_command))
    application.add_handler(CommandHandler("premium", premium_v2))
    
    # Admin commands
    application.add_handler(CommandHandler("admin", admin_dashboard))
    application.add_handler(CommandHandler("verify", verify_payment_admin))
    application.add_handler(CommandHandler("pending", pending_payments_admin))
    application.add_handler(CommandHandler("revenue", revenue_admin))
    application.add_handler(CommandHandler("backup", backup_admin))
    application.add_handler(CommandHandler("broadcast", broadcast_admin))
    
    # Callback query handler (must be last)
    application.add_handler(CallbackQueryHandler(button_handler_v2))
    
    # ======================
    # SCHEDULED TASKS
    # ======================
    job_queue = application.job_queue
    if job_queue:
        # Run scheduled tasks every hour
        job_queue.run_repeating(
            scheduled_tasks,
            interval=3600,  # 1 hour
            first=10  # Start after 10 seconds
        )
        
        logger.info("✅ Scheduled tasks configured")
    
    # ======================
    # ERROR HANDLER
    # ======================
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Try to notify user
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ An error occurred. Please try again or contact support."
                )
        except:
            pass
        
        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 Bot Error:\n\n{context.error}"
            )
        except:
            pass
    
    application.add_error_handler(error_handler)
    
    # ======================
    # START THE BOT
    # ======================
    logger.info(f"🚀 Starting {BOT_NAME} V2.10 with PostgreSQL...")
    logger.info(f"🤖 Bot Username: {BOT_USERNAME}")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"🗄️ Database: PostgreSQL")
    
    print(f"\n{'='*50}")
    print(f"🚀 {BOT_NAME} V2.10 PRODUCTION READY")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"👑 Admin: {ADMIN_ID}")
    print(f"🗄️ Database: PostgreSQL")
    print(f"📊 Tier System: Complete V2")
    print(f"{'='*50}\n")
    
    # Run in polling mode
    print("🔄 Starting in polling mode...")
    print("📱 Open Telegram and search for your bot to test!")
    print("⚡ Press Ctrl+C to stop the bot\n")
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

# ======================
# ENVIRONMENT SETUP
# ======================
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Run the bot
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
        print("\n👋 Bot stopped successfully")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n❌ Bot crashed with error: {e}")
