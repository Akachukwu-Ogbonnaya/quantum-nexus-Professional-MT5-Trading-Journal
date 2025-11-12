"""
COMPLETE PROFESSIONAL MT5 TRADING JOURNAL
- Universal JSON configuration adaptability
- Advanced trading analytics with calendar dashboard
- Real-time synchronization
- Professional UI/UX design
- Comprehensive error handling
- PostgreSQL + SQLite hybrid database support
"""

import os
import json
import threading
import queue
import time
import io
import csv
import calendar
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation

# -----------------------------------------------------------------------------
# DATABASE MODE SELECTION
# -----------------------------------------------------------------------------
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"

if USE_POSTGRES:
    # PostgreSQL mode (for deployment / Render)
    import psycopg
    from psycopg.rows import dict_row

    def cursor_with_dict(conn):
        """Return PostgreSQL dict-style cursor"""
        return conn.cursor(row_factory=dict_row)

    print("✅ PostgreSQL mode activated")
else:
    # SQLite fallback mode (for desktop/offline users)
    import sqlite3

    def cursor_with_dict(conn):
        """Return SQLite cursor with tuple access"""
        return conn.cursor()

    print("💾 SQLite mode activated (desktop/local mode)")

# -----------------------------------------------------------------------------
# FLASK CORE IMPORTS
# -----------------------------------------------------------------------------
from flask import (
    Flask, render_template, request, redirect, url_for, session,
    jsonify, send_file, abort, flash, Response
)
from flask_session import Session
from flask_wtf import CSRFProtect
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField, TextAreaField, FloatField
)
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional

# -----------------------------------------------------------------------------
# DATA ANALYSIS + LOGGING + SOCKETIO
# -----------------------------------------------------------------------------
import pandas as pd
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
from flask_socketio import SocketIO, emit
def get_db_connection():
    """Return a connection to the correct database based on environment"""
    if USE_POSTGRES:
        return psycopg.connect(
            dbname=os.getenv("POSTGRES_DB", "quantum_journal_db"),
            user=os.getenv("POSTGRES_USER", "quantum_user"),
            password=os.getenv("POSTGRES_PASSWORD", "quantum_pass"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
    else:
        db_path = os.path.join(os.getcwd(), "database", "quantum_journal.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return sqlite3.connect(db_path)

# =============================================================================
# PROFESSIONAL LICENSE MANAGEMENT SYSTEM
# =============================================================================
import hashlib
import uuid
import platform
import socket
import subprocess
from datetime import datetime, timedelta

class LicenseManager:
    def __init__(self):
        self.license_file = self.get_license_file_path()
        self.license_data = self.load_license()
        self.trial_days = 30  # 30-day free trial
        
    def get_license_file_path(self):
        """Get license file path based on OS"""
        system = platform.system().lower()
        
        if system == "windows":
            license_dir = os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal', 'license')
        elif system == "darwin":  # macOS
            license_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MT5Journal')
        else:  # Linux and other Unix-like
            license_dir = os.path.join(os.path.expanduser('~'), '.config', 'mt5journal', 'license')
        
        os.makedirs(license_dir, exist_ok=True)
        return os.path.join(license_dir, 'license.lic')
    
    def get_system_fingerprint(self):
        """Generate unique system fingerprint"""
        try:
            # Get system information
            system_info = {
                'machine': platform.machine(),
                'processor': platform.processor(),
                'system': platform.system(),
                'node': platform.node(),
                'mac_address': self.get_mac_address()
            }
            
            # Create hash from system info
            fingerprint_str = ''.join(str(v) for v in system_info.values())
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
            
        except Exception as e:
            # Fallback to random UUID if system info unavailable
            return str(uuid.uuid4())
    
    def get_mac_address(self):
        """Get MAC address for system identification"""
        try:
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except:
            return "00:00:00:00:00:00"
    
    def load_license(self):
        """Load license data from file"""
        default_license = {
            'status': 'trial',
            'created_date': datetime.now().isoformat(),
            'expiry_date': (datetime.now() + timedelta(days=self.trial_days)).isoformat(),
            'license_key': '',
            'system_fingerprint': self.get_system_fingerprint(),
            'activations': 0,
            'max_activations': 1,
            'features': ['basic_trading_journal', 'risk_analysis', 'trade_analytics']
        }
        
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r') as f:
                    license_data = json.load(f)
                    # Validate license integrity
                    if self.validate_license_integrity(license_data):
                        return license_data
                    else:
                        add_log('WARNING', 'License file tampered with, resetting to trial', 'License')
                        return default_license
            else:
                # Create initial trial license
                self.save_license(default_license)
                return default_license
                
        except Exception as e:
            add_log('ERROR', f'License loading error: {e}', 'License')
            return default_license
    
    def save_license(self, license_data):
        """Save license data to file"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            return True
        except Exception as e:
            add_log('ERROR', f'License saving error: {e}', 'License')
            return False
    
    def validate_license_integrity(self, license_data):
        """Validate license hasn't been tampered with"""
        try:
            required_fields = ['status', 'created_date', 'system_fingerprint']
            if not all(field in license_data for field in required_fields):
                return False
            
            # Check if system fingerprint matches
            current_fingerprint = self.get_system_fingerprint()
            if license_data.get('system_fingerprint') != current_fingerprint:
                add_log('WARNING', 'System fingerprint changed - possible license violation', 'License')
                return False
                
            return True
        except:
            return False
    
    def validate_license(self):
        """Validate current license status"""
        try:
            # Check if trial expired
            if self.license_data['status'] == 'trial':
                expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
                if datetime.now() > expiry_date:
                    self.license_data['status'] = 'expired'
                    self.save_license(self.license_data)
                    return False, "Trial period has expired"
                return True, f"Trial active - {self.get_trial_days_left()} days remaining"
            
            # Check if licensed
            elif self.license_data['status'] == 'licensed':
                # Validate license key
                if self.validate_license_key(self.license_data['license_key']):
                    return True, "License active"
                else:
                    return False, "Invalid license key"
            
            elif self.license_data['status'] == 'expired':
                return False, "License has expired"
                
            else:
                return False, "Invalid license status"
                
        except Exception as e:
            add_log('ERROR', f'License validation error: {e}', 'License')
            return False, "License validation error"
    
    def get_trial_days_left(self):
        """Get remaining trial days"""
        try:
            expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
            days_left = (expiry_date - datetime.now()).days
            return max(0, days_left)
        except:
            return 0
    
    def validate_license_key(self, license_key):
        """Validate license key format and signature"""
        try:
            if not license_key or len(license_key) != 29:
                return False
            
            # Simple validation - in production use proper cryptographic validation
            parts = license_key.split('-')
            if len(parts) != 4 or not all(len(part) == 7 for part in parts):
                return False
                
            return True
        except:
            return False
    
    def activate_license(self, license_key):
        """Activate a license key"""
        try:
            if self.validate_license_key(license_key):
                self.license_data.update({
                    'status': 'licensed',
                    'license_key': license_key,
                    'activation_date': datetime.now().isoformat(),
                    'activations': self.license_data.get('activations', 0) + 1,
                    'features': ['full_trading_journal', 'advanced_analytics', 'ai_coaching', 'priority_support']
                })
                
                if self.save_license(self.license_data):
                    add_log('INFO', f'License activated successfully: {license_key}', 'License')
                    return True, "License activated successfully!"
                else:
                    return False, "Failed to save license"
            else:
                return False, "Invalid license key format"
                
        except Exception as e:
            add_log('ERROR', f'License activation error: {e}', 'License')
            return False, f"Activation error: {str(e)}"
    
    def get_license_info(self):
        """Get comprehensive license information"""
        is_valid, message = self.validate_license()
        
        return {
            'status': self.license_data['status'],
            'is_valid': is_valid,
            'message': message,
            'trial_days_left': self.get_trial_days_left(),
            'features': self.license_data.get('features', []),
            'created_date': self.license_data.get('created_date'),
            'expiry_date': self.license_data.get('expiry_date'),
            'activations': self.license_data.get('activations', 0),
            'max_activations': self.license_data.get('max_activations', 1),
            'system_fingerprint': self.license_data.get('system_fingerprint')[:8] + '...'  # Partial for security
        }

# Initialize license manager
license_manager = LicenseManager()

# -----------------------------------------------------------------------------
# SQLite3 Date Deprecation Fix for Python 3.12+
# -----------------------------------------------------------------------------
def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()

def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 datetime."""
    return val.isoformat()


def convert_trade_dates(trades_list):
    """Convert string dates to datetime objects for template compatibility"""
    for trade in trades_list:
        # Convert entry_time if it's a string
        if isinstance(trade.get('entry_time'), str):
            try:
                trade['entry_time'] = datetime.fromisoformat(trade['entry_time'].replace('Z', '+00:00'))
            except:
                pass  # Keep as string if conversion fails

        # Convert exit_time if it's a string
        if isinstance(trade.get('exit_time'), str):
            try:
                trade['exit_time'] = datetime.fromisoformat(trade['exit_time'].replace('Z', '+00:00'))
            except:
                pass  # Keep as string if conversion fails
    return trades_list
# -----------------------------------------------------------------------------

# Optional libs (MT5 and reportlab)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 not installed - running in demo mode")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfgen import canvas
    reportlab_available = True
except ImportError:
    reportlab_available = False
    print("⚠️ ReportLab not installed - PDF generation disabled")

# -----------------------------------------------------------------------------
# SQLite3 Date Deprecation Fix for Python 3.12+
# -----------------------------------------------------------------------------
def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()

def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 datetime."""
    return val.isoformat()

def convert_date(val):
    """Convert ISO 8601 date to datetime.date object."""
    return date.fromisoformat(val.decode())

def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.fromisoformat(val.decode())

# Register the adapters and converters
sqlite3.register_adapter(date, adapt_date_iso)
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("date", convert_date)
sqlite3.register_converter("datetime", convert_datetime)

# -----------------------------------------------------------------------------
# Configuration Management with Universal Adaptability
# -----------------------------------------------------------------------------
class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load_or_create_config()

    def load_or_create_config(self):
        """Load existing config or create with universal template"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error loading config: {e}")
                return self.create_default_config()
        else:
            return self.create_default_config()

    def create_default_config(self):
        """Create universal config that adapts to any MT5 account"""
        default_config = {
            "mt5": {
                "terminal_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                "account": 0,  # Will be dynamically set
                "password": "",  # Will be dynamically set
                "server": ""  # Will be dynamically set
            },
            "web_app": {
                "secret_key": "mt5-journal-pro-" + os.urandom(24).hex(),
                "host": "127.0.0.1",
                "port": 5000,
                "debug": False
            },
            "database": {
                "path": "database/trades.db",
                "backup_interval_hours": 24
            },
            "sync": {
                "auto_sync_interval": 300,
                "days_history": 90,
                "real_time_updates": True
            },
            "ui": {
                "theme": "dark",
                "charts_enabled": True,
                "notifications": True
            }
        }

        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=4)
            print(f"✅ Created universal config at {self.config_path}")
        except Exception as e:
            print(f"❌ Error creating config: {e}")

        return default_config

    def update_mt5_config(self, account, password, server, terminal_path=None):
        """Update MT5 configuration dynamically"""
        try:
            self.config["mt5"]["account"] = account
            self.config["mt5"]["password"] = password
            self.config["mt5"]["server"] = server
            if terminal_path:
                self.config["mt5"]["terminal_path"] = terminal_path

            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            print(f"✅ Updated MT5 config for account: {account}")
            return True
        except Exception as e:
            print(f"❌ Error updating MT5 config: {e}")
            return False

# Initialize config manager
config_manager = ConfigManager()
config = config_manager.config

# =============================================================================
# FIX 1: FORCE CONFIG RELOAD TO ENSURE SYNC SECTION EXISTS
# =============================================================================
import json

try:
    # Reload config to ensure it has all required sections
    with open("config.json", "r") as f:
        config = json.load(f)

    # ENSURE SYNC SECTION EXISTS
    if 'sync' not in config:
        config['sync'] = {
            'auto_sync_interval': 300,
            'days_history': 90,
            'real_time_updates': True
        }
        # Save the updated config
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        print("✅ Added missing 'sync' section to config.json")

    # Ensure all required sections exist
    required_sections = ['database', 'ui']
    for section in required_sections:
        if section not in config:
            config[section] = {}
            print(f"✅ Added missing '{section}' section to config")

except Exception as e:
    print(f"⚠️ Config reload warning: {e}")

# =============================================================================
# MT5 Connection Manager with Universal Adaptability
# =============================================================================
class UniversalMT5Manager:
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.last_connection = None
        self.connection_attempts = 0
        self.max_attempts = 3

    def initialize_connection(self, account=None, password=None, server=None, terminal_path=None):
        """Initialize MT5 connection with dynamic configuration"""
        if not MT5_AVAILABLE:
            print("⚠️ MT5 not available - running in demo mode")
            return self.initialize_demo_mode()

        try:
            # Use provided credentials or config defaults
            mt5_config = config.get("mt5", {})
            account = account or mt5_config.get("account", 0)
            password = password or mt5_config.get("password", "")
            server = server or mt5_config.get("server", "")
            terminal_path = terminal_path or mt5_config.get("terminal_path", "")

            if not all([account, password, server]):
                print("❌ MT5 credentials incomplete - please update config.json")
                return self.initialize_demo_mode()

            print(f"🔗 Connecting to MT5: Account={account}, Server={server}")

            # Initialize MT5
            if not mt5.initialize(
                path=terminal_path,
                login=int(account),
                password=password,
                server=server
            ):
                error = mt5.last_error()
                print(f"❌ MT5 initialization failed: {error}")

                # Update config if credentials might be wrong
                if error in [10013, 10014, 10015]:  # Auth errors
                    print("🔐 Authentication failed - please check credentials in config.json")

                return self.initialize_demo_mode()

            # Verify connection
            self.account_info = mt5.account_info()
            if self.account_info:
                self.connected = True
                self.last_connection = datetime.now()
                self.connection_attempts = 0

                # Update config with successful connection details
                config_manager.update_mt5_config(account, password, server, terminal_path)

                print(f"✅ Connected to MT5 Account: {self.account_info.login}")
                print(f"   Balance: ${self.account_info.balance:.2f}")
                print(f"   Server: {self.account_info.server}")
                print(f"   Currency: {self.account_info.currency}")
                return True
            else:
                print("❌ Failed to get account info")
                return self.initialize_demo_mode()

        except Exception as e:
            print(f"❌ MT5 connection error: {e}")
            self.connection_attempts += 1
            return self.initialize_demo_mode()

    def initialize_demo_mode(self):
        """Initialize demo mode when MT5 is not available"""
        print("🔄 Initializing demo mode with sample data")
        self.connected = False
        self.account_info = type('AccountInfo', (), {
            'login': 11146004,
            'balance': 10000.0,
            'equity': 11520.5,
            'margin': 1250.0,
            'margin_free': 10270.5,
            'leverage': 100,
            'currency': 'USD',
            'server': 'Demo-Server'
        })()
        return True

    def reconnect(self):
        """Attempt to reconnect to MT5"""
        if self.connection_attempts >= self.max_attempts:
            print("🔴 Max connection attempts reached - staying in demo mode")
            return False

        print("🔄 Attempting MT5 reconnection...")
        return self.initialize_connection()

    def shutdown(self):
        """Shutdown MT5 connection"""
        if MT5_AVAILABLE and self.connected:
            try:
                mt5.shutdown()
                self.connected = False
                print("🔴 MT5 connection closed")
            except Exception as e:
                print(f"⚠️ Error closing MT5 connection: {e}")

# Initialize MT5 Manager
mt5_manager = UniversalMT5Manager()

# Initialize MT5 Manager
mt5_manager = UniversalMT5Manager()

# =============================================================================
# HYBRID DATABASE UTILITY FUNCTIONS
# =============================================================================

def get_universal_connection():
    """Universal connection that works for both PostgreSQL and SQLite"""
    return db_manager.get_connection()

def universal_execute(cursor, query, params=None):
    """Execute query with universal parameter style"""
    # Get database type from cursor or connection
    db_type = getattr(cursor, 'db_type', None)
    if not db_type and hasattr(cursor, 'connection'):
        db_type = getattr(cursor.connection, 'db_type', 'sqlite')
    
    # Convert parameter style if needed
    if db_type == 'postgresql' and '?' in query:
        query = query.replace('?', '%s')
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

def conn_fetch_dataframe(conn, query, params=None):
    """Universal dataframe fetch for both databases"""
    try:
        if params:
            return pd.read_sql_query(query, conn, params=params)
        else:
            return pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Dataframe fetch error: {e}")
        return pd.DataFrame()

def detect_environment():
    """Enhanced environment detection for hybrid mode"""
    # Web environment indicators
    web_indicators = [
        'DATABASE_URL' in os.environ,
        'RAILWAY_ENVIRONMENT' in os.environ,
        'HEROKU' in os.environ,
        'RENDER' in os.environ,
        'FLY_APP_NAME' in os.environ,
        any('pythonanywhere' in key.lower() for key in os.environ.keys())
    ]
    
    if any(web_indicators):
        return 'postgresql'
    else:
        return 'sqlite'

def get_demo_risk_recommendations():
    """Demo risk recommendations"""
    return [
        {
            'category': 'Position Sizing',
            'message': 'Consider reducing position sizes by 25% to manage volatility',
            'priority': 'medium'
        },
        {
            'category': 'Diversification', 
            'message': 'Diversify across more symbols to reduce concentration risk',
            'priority': 'medium'
        }
    ]

def get_demo_detailed_risk_metrics():
    """Demo detailed risk metrics"""
    return [
        {
            'name': 'Max Drawdown',
            'value': '15.5%',
            'benchmark': '< 10%', 
            'status': 'Good',
            'description': 'Maximum peak-to-trough decline in equity'
        },
        {
            'name': 'Sharpe Ratio',
            'value': '1.2',
            'benchmark': '> 1.0',
            'status': 'Excellent',
            'description': 'Risk-adjusted return metric'
        }
    ]

def get_demo_risk_chart_data():
    """Demo risk chart data"""
    return {
        'labels': ['Trade 1', 'Trade 2', 'Trade 3', 'Trade 4', 'Trade 5'],
        'risk_values': [2.5, 3.1, 1.8, 4.2, 2.9]
    }

def get_demo_drawdown_chart_data():
    """Demo drawdown chart data"""
    return {
        'dates': ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
        'drawdowns': [0, 2.5, 1.8, 4.2, 3.1]
    }

def get_demo_concentration_chart_data():
    """Demo concentration chart data"""
    return {
        'labels': ['EURUSD', 'GBPUSD', 'XAUUSD', 'USDJPY', 'Others'],
        'values': [35, 25, 20, 15, 5]
    }

class HybridErrorHandler:
    """Handle errors differently for web vs desktop"""
    
    @staticmethod
    def handle_database_error(error, context="Database operation"):
        """Handle database errors appropriately for environment"""
        environment = detect_environment()
        
        if environment == 'postgresql':
            # For web: Log and return JSON error
            add_log('ERROR', f'{context} failed: {error}', 'Database')
            return {'success': False, 'error': 'Database operation failed'}
        else:
            # For desktop: Attempt recovery or use demo data
            add_log('WARNING', f'{context} failed, using demo data: {error}', 'Database')
            return {'success': True, 'demo_mode': True, 'message': 'Using demo data'}

class DatabaseMigrator:
    """Handle database migration between SQLite and PostgreSQL"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def export_to_sqlite(self, postgres_conn, sqlite_path):
        """Export from PostgreSQL to SQLite"""
        try:
            tables = ['trades', 'users', 'account_history', 'calendar_pnl', 'trade_plans', 'market_analysis']
            
            for table in tables:
                # Read from PostgreSQL
                df = pd.read_sql(f'SELECT * FROM {table}', postgres_conn)
                
                # Write to SQLite
                with sqlite3.connect(sqlite_path) as sqlite_conn:
                    df.to_sql(table, sqlite_conn, if_exists='replace', index=False)
            
            return True
        except Exception as e:
            add_log('ERROR', f'Export to SQLite failed: {e}', 'Migration')
            return False

import functools

def hybrid_compatible(route_func):
    """Decorator to make routes work in both web and desktop modes"""
    @functools.wraps(route_func)
    def wrapper(*args, **kwargs):
        try:
            return route_func(*args, **kwargs)
        except Exception as e:
            # Log the error
            add_log('ERROR', f'Route {route_func.__name__} error: {e}', 'Hybrid')
            
            # Return appropriate response based on environment
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Operation failed', 'demo_mode': True})
            else:
                flash('Operation completed in demo mode', 'info')
                return redirect(request.referrer or url_for('professional_dashboard'))
    return wrapper

def initialize_hybrid_application():
    """Initialize application for hybrid mode"""
    environment = detect_environment()
    
    print(f"🚀 Starting Professional MT5 Journal in {environment.upper()} mode")
    
    # Initialize database
    try:
        init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
        # Continue in demo mode
    
    # Initialize MT5 connection based on environment
    if environment == 'sqlite' and MT5_AVAILABLE:
        print("🔗 Attempting MT5 connection for desktop mode...")
        mt5_manager.initialize_connection()
    else:
        print("🌐 Web mode or MT5 unavailable - using demo data")
        mt5_manager.initialize_demo_mode()
    
    print("✅ Hybrid application initialization complete")

# Call the initialization
initialize_hybrid_application()


# -----------------------------------------------------------------------------
# Flask Application Setup
# -----------------------------------------------------------------------------
app = Flask(__name__,
           static_folder='static',
           template_folder='templates',
           static_url_path='/static')

app.secret_key = config['web_app'].get('secret_key', 'mt5-journal-pro-secret-2024')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Session management
Session(app)

# CSRF Protection
csrf = CSRFProtect(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# SocketIO for real-time features
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   ping_interval=25,
                   ping_timeout=60,
                   async_mode='threading')

# -----------------------------------------------------------------------------
# Advanced Logging Setup
# -----------------------------------------------------------------------------
class AdvancedLogger:
    def __init__(self):
        self.log_messages = []
        self.max_log_messages = 5000

        # Setup file logging
        if not os.path.exists('logs'):
            os.makedirs('logs')

        log_handler = RotatingFileHandler(
            'logs/mt5_journal.log',
            maxBytes=10_000_000,  # 10MB
            backupCount=10
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        log_handler.setFormatter(formatter)

        logger = logging.getLogger("mt5_journal")
        logger.setLevel(logging.INFO)
        logger.addHandler(log_handler)

        self.logger = logger

    def add_log(self, level, message, source="System"):
        """Add log entry with timestamp and source"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            'timestamp': timestamp,
            'level': level.upper(),
            'source': source,
            'message': message
        }

        self.log_messages.append(entry)
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages.pop(0)

        # Log to file
        if level.upper() == 'ERROR':
            self.logger.error(f"[{source}] {message}")
        elif level.upper() == 'WARNING':
            self.logger.warning(f"[{source}] {message}")
        elif level.upper() == 'DEBUG':
            self.logger.debug(f"[{source}] {message}")
        else:
            self.logger.info(f"[{source}] {message}")

        # Emit to connected clients
        try:
            socketio.emit('log_update', entry, namespace='/realtime')
        except Exception:
            pass

# Initialize logger
advanced_logger = AdvancedLogger()
add_log = advanced_logger.add_log

add_log('INFO', 'Professional MT5 Trading Journal Started', 'System')

# -----------------------------------------------------------------------------
# HYBRID DATABASE MANAGER - AUTOMATIC ENVIRONMENT DETECTION
# -----------------------------------------------------------------------------
class HybridDatabaseManager:
    def __init__(self):
        self.db_type = self.detect_environment()
        self.connection = None
        print(f"🔍 Environment detected: {self.db_type.upper()} mode")
    
    def detect_environment(self):
        """Auto-detect if running as web app or desktop app"""
        # Web environment indicators
        web_indicators = [
            'DATABASE_URL' in os.environ,
            'RAILWAY_ENVIRONMENT' in os.environ,
            'HEROKU' in os.environ,
            'RENDER' in os.environ,
            any('pythonanywhere' in key.lower() for key in os.environ.keys())
        ]
        
        if any(web_indicators):
            return 'postgresql'
        else:
            return 'sqlite'
    
    def get_connection(self):
        """Get appropriate database connection based on environment"""
        if self.db_type == 'postgresql':
            return self.get_postgresql_connection()
        else:
            return self.get_sqlite_connection()
    
    def get_postgresql_connection(self):
        """Get PostgreSQL connection for web environment"""
        try:
            database_url = os.environ.get('DATABASE_URL')
            if database_url and database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            if database_url:
                conn = psycopg.connect(database_url, row_factory=dict_row)
                conn.db_type = 'postgresql'
                return conn
            else:
                # Fallback to local PostgreSQL
                conn = psycopg.connect(
                    host=os.environ.get('PGHOST', 'localhost'),
                    dbname=os.environ.get('PGDATABASE', 'mt5_journal'),
                    user=os.environ.get('PGUSER', 'postgres'),
                    password=os.environ.get('PGPASSWORD', ''),
                    port=os.environ.get('PGPORT', 5432),
                    row_factory=dict_row
                )
                conn.db_type = 'postgresql'
                return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}, falling back to SQLite")
            return self.get_sqlite_connection()
    
    def get_sqlite_connection(self):
        """Get SQLite connection for desktop environment"""
        try:
            # Define DB_PATH for SQLite
            DB_PATH = config['database'].get('path', 'database/trades.db')
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            
            # Connect with date adapters
            conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            conn.db_type = 'sqlite'
            
            # Enable foreign keys and WAL mode for better performance
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            
            return conn
        except Exception as e:
            print(f"❌ SQLite connection failed: {e}")
            raise
    
    def execute_query(self, query, params=None):
        """Execute query with appropriate parameter style for current database"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Convert parameter style if needed
            if self.db_type == 'postgresql' and '?' in query:
                query = query.replace('?', '%s')
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                # Convert to dict for consistency
                if self.db_type == 'postgresql':
                    return [dict(row) for row in result]
                else:
                    return [dict(row) for row in result]
            else:
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# Initialize hybrid database manager
db_manager = HybridDatabaseManager()

# Universal connection function for backward compatibility
def get_db_connection():
    """Universal database connection that works in both environments"""
    return db_manager.get_connection()

# Define DB_PATH for SQLite fallback (used in existing code)
DB_PATH = config['database'].get('path', 'database/trades.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# -----------------------------------------------------------------------------
# HYBRID DATABASE INITIALIZATION
# -----------------------------------------------------------------------------
def init_database():
    """Initialize database with hybrid schema compatibility"""
    conn = db_manager.get_connection()
    
    try:
        if conn.db_type == 'postgresql':
            init_postgresql_schema(conn)
        else:
            init_sqlite_schema(conn)
        
        print(f"✅ {conn.db_type.upper()} database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise
    finally:
        conn.close()

def init_postgresql_schema(conn):
    """Initialize PostgreSQL schema"""
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email VARCHAR(120),
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Enhanced trades table (PostgreSQL syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER UNIQUE,
            symbol VARCHAR(50) NOT NULL,
            type VARCHAR(20) CHECK(type IN ('BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP')),
            volume REAL NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            exit_price REAL,
            sl_price REAL,
            tp_price REAL,
            entry_time TIMESTAMP NOT NULL,
            exit_time TIMESTAMP,
            profit REAL DEFAULT 0,
            commission REAL DEFAULT 0,
            swap REAL DEFAULT 0,
            comment TEXT,
            magic_number INTEGER,
            session VARCHAR(50),
            planned_rr REAL,
            actual_rr REAL,
            duration VARCHAR(50),
            account_balance REAL,
            account_equity REAL,
            account_change_percent REAL,
            status VARCHAR(20) CHECK(status IN ('OPEN', 'CLOSED', 'PENDING', 'CANCELLED')) DEFAULT 'OPEN',
            floating_pnl REAL DEFAULT 0,
            risk_per_trade REAL,
            margin_used REAL,
            strategy VARCHAR(100),
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Account history for equity curve (PostgreSQL syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_history (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            margin REAL,
            free_margin REAL,
            leverage INTEGER,
            currency VARCHAR(10),
            server VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Calendar PnL for daily performance (PostgreSQL syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_pnl (
            id SERIAL PRIMARY KEY,
            date DATE UNIQUE NOT NULL,
            daily_pnl REAL NOT NULL DEFAULT 0,
            closed_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            break_even_trades INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            avg_win REAL DEFAULT 0,
            avg_loss REAL DEFAULT 0,
            largest_win REAL DEFAULT 0,
            largest_loss REAL DEFAULT 0,
            total_volume REAL DEFAULT 0,
            daily_goal REAL DEFAULT 0,
            goal_achieved BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Trade plans table (PostgreSQL syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_plans (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            trade_plan TEXT,
            direction VARCHAR(10) CHECK(direction IN ('LONG', 'SHORT', 'BOTH')),
            condition TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            target_profit REAL,
            risk_reward_ratio REAL,
            confidence_level INTEGER CHECK(confidence_level >= 1 AND confidence_level <= 5),
            status VARCHAR(20) CHECK(status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'EXPIRED')) DEFAULT 'PENDING',
            outcome TEXT,
            actual_profit REAL,
            notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Market analysis table (PostgreSQL syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_analysis (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            timeframe VARCHAR(20),
            analysis_type VARCHAR(50),
            sentiment VARCHAR(20),
            key_levels TEXT,
            news_impact TEXT,
            technical_analysis TEXT,
            fundamental_analysis TEXT,
            risk_level VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades(ticket_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_pnl(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_history_timestamp ON account_history(timestamp)')
    
    conn.commit()

def init_sqlite_schema(conn):
    """Initialize SQLite schema with compatible syntax"""
    cursor = conn.cursor()
    
    # Users table (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            preferences TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    ''')
    
    # Enhanced trades table (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER UNIQUE,
            symbol TEXT NOT NULL,
            type TEXT CHECK(type IN ('BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP')),
            volume REAL NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            exit_price REAL,
            sl_price REAL,
            tp_price REAL,
            entry_time DATETIME NOT NULL,
            exit_time DATETIME,
            profit REAL DEFAULT 0,
            commission REAL DEFAULT 0,
            swap REAL DEFAULT 0,
            comment TEXT,
            magic_number INTEGER,
            session TEXT,
            planned_rr REAL,
            actual_rr REAL,
            duration TEXT,
            account_balance REAL,
            account_equity REAL,
            account_change_percent REAL,
            status TEXT CHECK(status IN ('OPEN', 'CLOSED', 'PENDING', 'CANCELLED')) DEFAULT 'OPEN',
            floating_pnl REAL DEFAULT 0,
            risk_per_trade REAL,
            margin_used REAL,
            strategy TEXT,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Account history for equity curve (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            margin REAL,
            free_margin REAL,
            leverage INTEGER,
            currency TEXT,
            server TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Calendar PnL for daily performance (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_pnl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE NOT NULL,
            daily_pnl REAL NOT NULL DEFAULT 0,
            closed_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            break_even_trades INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            avg_win REAL DEFAULT 0,
            avg_loss REAL DEFAULT 0,
            largest_win REAL DEFAULT 0,
            largest_loss REAL DEFAULT 0,
            total_volume REAL DEFAULT 0,
            daily_goal REAL DEFAULT 0,
            goal_achieved BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Trade plans table (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            symbol TEXT NOT NULL,
            trade_plan TEXT,
            direction TEXT CHECK(direction IN ('LONG', 'SHORT', 'BOTH')),
            condition TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            target_profit REAL,
            risk_reward_ratio REAL,
            confidence_level INTEGER CHECK(confidence_level >= 1 AND confidence_level <= 5),
            status TEXT CHECK(status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'EXPIRED')) DEFAULT 'PENDING',
            outcome TEXT,
            actual_profit REAL,
            notes TEXT,
            image_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Market analysis table (SQLite syntax)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            analysis_type TEXT,
            sentiment TEXT,
            key_levels TEXT,
            news_impact TEXT,
            technical_analysis TEXT,
            fundamental_analysis TEXT,
            risk_level TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades(ticket_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_pnl(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_history_timestamp ON account_history(timestamp)')
    
    conn.commit()

# Initialize database
init_database()
# -----------------------------------------------------------------------------
# User Management (Hybrid PostgreSQL/SQLite Version)
# -----------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, id_, username, password_hash, email=None, preferences=None):
        self.id = id_
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.preferences = preferences or {}

    @staticmethod
    def get(user_id):
        """Get user by ID - hybrid compatible"""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            
            # Database-specific query
            if conn.db_type == 'postgresql':
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE id = %s', (user_id,))
            else:
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE id = ?', (user_id,))
            
            row = cursor.fetchone()
            if row:
                # Convert to dict for consistent access
                if conn.db_type == 'postgresql':
                    user_data = dict(row)
                else:
                    user_data = dict(zip([col[0] for col in cursor.description], row))
                
                # Parse preferences JSON
                prefs = user_data.get('preferences', '{}')
                if prefs and prefs != '{}':
                    try:
                        preferences = json.loads(prefs)
                    except:
                        preferences = {}
                else:
                    preferences = {}
                
                return User(
                    user_data['id'], 
                    user_data['username'], 
                    user_data['password_hash'], 
                    user_data.get('email'), 
                    preferences
                )
            return None
            
        except Exception as e:
            print(f"User.get error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_by_username(username):
        """Get user by username - hybrid compatible"""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            
            # Database-specific query
            if conn.db_type == 'postgresql':
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE username = %s', (username,))
            else:
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE username = ?', (username,))
            
            row = cursor.fetchone()
            if row:
                # Convert to dict for consistent access
                if conn.db_type == 'postgresql':
                    user_data = dict(row)
                else:
                    user_data = dict(zip([col[0] for col in cursor.description], row))
                
                # Parse preferences JSON
                prefs = user_data.get('preferences', '{}')
                if prefs and prefs != '{}':
                    try:
                        preferences = json.loads(prefs)
                    except:
                        preferences = {}
                else:
                    preferences = {}
                
                return User(
                    user_data['id'], 
                    user_data['username'], 
                    user_data['password_hash'], 
                    user_data.get('email'), 
                    preferences
                )
            return None
            
        except Exception as e:
            print(f"User.get_by_username error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def create(username, password, email=None):
        """Create new user - hybrid compatible"""
        password_hash = generate_password_hash(password)
        preferences = json.dumps({'theme': 'dark', 'notifications': True})

        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                # PostgreSQL uses %s placeholders and RETURNING id
                cursor.execute(
                    'INSERT INTO users (username, password_hash, email, preferences) VALUES (%s, %s, %s, %s) RETURNING id',
                    (username, password_hash, email, preferences)
                )
                user_id = cursor.fetchone()[0]
            else:
                # SQLite uses ? placeholders and lastrowid
                cursor.execute(
                    'INSERT INTO users (username, password_hash, email, preferences) VALUES (?, ?, ?, ?)',
                    (username, password_hash, email, preferences)
                )
                user_id = cursor.lastrowid
            
            conn.commit()
            return User(user_id, username, password_hash, email, json.loads(preferences))
            
        except Exception as e:
            conn.rollback()
            # Handle unique constraint violation for both databases
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                print(f"Username already exists: {username}")
                return None
            else:
                print(f"Database error in User.create: {e}")
                return None
        finally:
            conn.close()

    def update_last_login(self):
        """Update last login timestamp - hybrid compatible"""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s', (self.id,))
            else:
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (self.id,))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error updating last login: {e}")
        finally:
            conn.close()

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))
    
# -----------------------------------------------------------------------------
# ADVANCED TRADING CALCULATIONS & ANALYTICS
# -----------------------------------------------------------------------------
def safe_float_conversion(value, default=0.0):
    """Safely convert any value to float with comprehensive error handling"""
    if value is None:
        return default

    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.replace(',', '').replace('$', '').replace(' ', '').strip()
            if cleaned:
                return float(cleaned)
        return default
    except (ValueError, TypeError, InvalidOperation):
        return default

class ProfessionalTradingCalculator:
    """Comprehensive professional trading calculations"""

    @staticmethod
    def calculate_risk_reward(entry_price, exit_price, sl_price, trade_type):
        """Advanced risk-reward calculation with validation"""
        entry = safe_float_conversion(entry_price)
        exit = safe_float_conversion(exit_price)
        sl = safe_float_conversion(sl_price)

        if sl == 0 or entry == 0 or entry == sl:
            return None

        try:
            trade_type = str(trade_type).upper().strip()

            if trade_type in ['BUY', 'BUY_LIMIT', 'BUY_STOP']:
                risk = entry - sl
                reward = exit - entry
            elif trade_type in ['SELL', 'SELL_LIMIT', 'SELL_STOP']:
                risk = sl - entry
                reward = entry - exit
            else:
                return None

            if risk != 0:
                rr_ratio = reward / risk
                return round(rr_ratio, 3)

        except Exception as e:
            add_log('ERROR', f'Risk-reward calculation error: {e}', 'Calculator')
            return None

    @staticmethod
    def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss, symbol=None):
        """Professional position sizing with symbol consideration"""
        try:
            account_balance = safe_float_conversion(account_balance)
            risk_amount = account_balance * (safe_float_conversion(risk_percent) / 100)
            price_diff = abs(safe_float_conversion(entry_price) - safe_float_conversion(stop_loss))

            if price_diff > 0:
                position_size = risk_amount / price_diff

                # Apply reasonable limits
                max_position = account_balance * 0.1  # Max 10% of account per trade
                position_size = min(position_size, max_position)

                return round(position_size, 4)
        except Exception as e:
            add_log('ERROR', f'Position size calculation error: {e}', 'Calculator')
        return 0

    @staticmethod
    def calculate_trade_duration(entry_time, exit_time):
        """Calculate trade duration with professional formatting"""
        try:
            if isinstance(entry_time, str):
                entry_time = pd.to_datetime(entry_time)
            if isinstance(exit_time, str):
                exit_time = pd.to_datetime(exit_time)

            if not exit_time or pd.isna(exit_time):
                return "Active"

            duration = exit_time - entry_time
            total_seconds = duration.total_seconds()

            if total_seconds < 60:
                return f"{int(total_seconds)}s"
            elif total_seconds < 3600:
                minutes = int(total_seconds / 60)
                seconds = int(total_seconds % 60)
                return f"{minutes}m {seconds}s"
            elif total_seconds < 86400:
                hours = int(total_seconds / 3600)
                minutes = int((total_seconds % 3600) / 60)
                return f"{hours}h {minutes}m"
            else:
                days = int(total_seconds / 86400)
                hours = int((total_seconds % 86400) / 3600)
                return f"{days}d {hours}h"
        except Exception as e:
            add_log('ERROR', f'Duration calculation error: {e}', 'Calculator')
            return "N/A"

    @staticmethod
    def calculate_pip_value(symbol, volume, account_currency="USD"):
        """Calculate pip value for risk management"""
        # Simplified pip value calculation
        # In production, this would use current prices and proper pip calculations
        try:
            volume = safe_float_conversion(volume)
            if 'JPY' in symbol:
                pip_value = volume * 0.01
            else:
                pip_value = volume * 0.0001
            return round(pip_value, 2)
        except Exception:
            return 0

    @staticmethod
    def calculate_max_drawdown(equity_curve):
        """Calculate maximum drawdown with professional handling"""
        if not equity_curve or len(equity_curve) == 0:
            return 0

        try:
            peak = equity_curve[0]
            max_drawdown = 0

            for value in equity_curve:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            return round(max_drawdown, 2)
        except Exception as e:
            add_log('ERROR', f'Max drawdown calculation error: {e}', 'Calculator')
            return 0

    @staticmethod
    def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
        """Advanced Sharpe ratio calculation"""
        if len(returns) < 2:
            return 0

        try:
            excess_returns = np.array(returns) - (risk_free_rate / 252)
            if np.std(excess_returns) == 0:
                return 0
            sharpe = (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)
            return round(sharpe, 3)
        except Exception as e:
            add_log('ERROR', f'Sharpe ratio calculation error: {e}', 'Calculator')
            return 0

    @staticmethod
    def calculate_recovery_factor(profits):
        """Recovery Factor (Net Profit / Max Drawdown)"""
        if len(profits) == 0:
            return 0

        try:
            cumulative = profits.cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_drawdown = abs(drawdown.min()) if drawdown.min() < 0 else 0.01

            if max_drawdown == 0:
                return float('inf') if cumulative.iloc[-1] > 0 else 0

            recovery = cumulative.iloc[-1] / max_drawdown
            return round(recovery, 2)
        except Exception as e:
            add_log('ERROR', f'Recovery factor calculation error: {e}', 'Calculator')
            return 0

    @staticmethod
    def calculate_expectancy(win_rate, avg_win, avg_loss):
        """Trading Expectancy with professional validation"""
        try:
            loss_rate = 1 - win_rate
            expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)
            return round(expectancy, 2)
        except Exception as e:
            add_log('ERROR', f'Expectancy calculation error: {e}', 'Calculator')
            return 0

    @staticmethod
    def calculate_kelly_criterion(win_rate, avg_win, avg_loss):
        """Kelly Criterion for position sizing"""
        try:
            if avg_loss == 0:
                return 0
            win_ratio = abs(avg_win / avg_loss)
            kelly = win_rate - ((1 - win_rate) / win_ratio)
            return max(0, round(kelly * 100, 2))  # Return as percentage
        except Exception as e:
            add_log('ERROR', f'Kelly criterion calculation error: {e}', 'Calculator')
            return 0

    @staticmethod
    def calculate_consecutive_streaks(profits):
        """Calculate consecutive winning and losing streaks"""
        if len(profits) == 0:
            return 0, 0

        try:
            wins = profits > 0
            losses = profits < 0

            def max_streak(series):
                max_count = current_count = 0
                for val in series:
                    if val:
                        current_count += 1
                        max_count = max(max_count, current_count)
                    else:
                        current_count = 0
                return max_count

            return max_streak(wins), max_streak(losses)
        except Exception as e:
            add_log('ERROR', f'Streak calculation error: {e}', 'Calculator')
            return 0, 0

    @staticmethod
    def calculate_account_change_percent(balance, equity):
        """Calculate account change percentage"""
        try:
            if balance == 0:
                return 0
            return ((equity - balance) / balance) * 100
        except Exception as e:
            add_log('ERROR', f'Account change calculation error: {e}', 'Calculator')
            return 0

# Initialize professional calculator
trading_calc = ProfessionalTradingCalculator()

# ======== TEMPLATE HELPER FUNCTIONS FOR JOURNAL ========
# ADDED: Required template helper functions for journal route

def create_empty_stats():
    """Create empty statistics with all required fields for template"""
    return {
        'max_drawdown': 0.0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'total_trades': 0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'sharpe_ratio': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'largest_win': 0.0,
        'largest_loss': 0.0,
        'current_drawdown': 0.0,
        'expectancy': 0.0,
        'risk_reward_ratio': 0.0,
        'net_profit': 0.0,
        'winning_trades': 0,
        'losing_trades': 0,
        'avg_trade': 0.0,
        'profit_loss_ratio': 0.0,
        'starting_balance': 0.0,
        'today_pnl': 0.0,
        'week_pnl': 0.0,
        'month_pnl': 0.0,
        'quarter_pnl': 0.0,
        'half_year_pnl': 0.0,
        'year_pnl': 0.0,
        'today_change': 0.0,
        'week_change': 0.0,
        'month_change': 0.0,
        'quarter_change': 0.0,
        'half_year_change': 0.0,
        'year_change': 0.0,
        'avg_risk_per_trade': 0.0,
        'break_even_trades': 0,
        'avg_rr': 0.0,
        'median_rr': 0.0,
        'best_trade_pct': 0.0,
        'worst_trade_pct': 0.0,
        'consecutive_wins': 0,
        'consecutive_losses': 0,
        'recovery_factor': 0.0,
        'kelly_criterion': 0.0,
        'avg_position_size': 0.0,
        'total_volume': 0.0,
        'risk_per_trade_avg': 0.0,
        'avg_trade_duration': "N/A",
        'best_symbol': "N/A",
        'worst_symbol': "N/A",
        'total_symbols_traded': 0,
        'period': "All Time"
    }

def calculate_planned_rr(trade):
    """Calculate planned risk/reward ratio"""
    try:
        if trade.get('planned_rr'):
            return float(trade['planned_rr'])
        return None
    except:
        return None

def calculate_actual_rr(trade):
    """Calculate actual risk/reward ratio"""
    try:
        if trade.get('actual_rr'):
            return float(trade['actual_rr'])
        return None
    except:
        return None

def calculate_trade_duration(trade):
    """Calculate trade duration"""
    try:
        if trade.get('duration'):
            return trade['duration']
        return None
    except:
        return None

def calculate_pnl_percent(trade):
    """Calculate P/L percentage"""
    try:
        if trade.get('profit') and trade.get('account_balance'):
            return (float(trade['profit']) / float(trade['account_balance'])) * 100
        return 0.0
    except:
        return 0.0

def calculate_account_change(trade, trades, index):
    """Calculate account change percentage"""
    try:
        if trade.get('account_change_percent'):
            return float(trade['account_change_percent'])
        return 0.0
    except:
        return 0.0

def get_trade_status(trade):
    """Get trade status"""
    try:
        return trade.get('status', 'UNKNOWN')
    except:
        return 'UNKNOWN'

# -----------------------------------------------------------------------------
# COMPREHENSIVE STATISTICS GENERATOR
# -----------------------------------------------------------------------------
class ProfessionalStatisticsGenerator:
    """Generate comprehensive professional trading statistics"""

    @staticmethod
    def generate_trading_statistics(df, period="All Time"):
        """Generate complete trading statistics with period analysis"""
        if df.empty:
            return create_empty_stats()

        try:
            # Basic metrics
            total_trades = len(df)
            winning_trades = len(df[df['profit'] > 0])
            losing_trades = len(df[df['profit'] < 0])
            break_even_trades = len(df[df['profit'] == 0])

            # Profit calculations
            net_profit = float(df['profit'].sum())
            gross_profit = float(df[df['profit'] > 0]['profit'].sum())
            gross_loss = abs(float(df[df['profit'] < 0]['profit'].sum()))

            # Rate calculations
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

            # Average calculations
            avg_win = float(df[df['profit'] > 0]['profit'].mean()) if winning_trades > 0 else 0
            avg_loss = float(df[df['profit'] < 0]['profit'].mean()) if losing_trades > 0 else 0
            avg_trade = float(df['profit'].mean()) if total_trades > 0 else 0

            # Risk-Reward calculations
            rr_ratios = pd.to_numeric(df['actual_rr'], errors='coerce').dropna()
            avg_rr = float(rr_ratios.mean()) if len(rr_ratios) > 0 else 0
            median_rr = float(rr_ratios.median()) if len(rr_ratios) > 0 else 0

            # Extreme values
            largest_win = float(df['profit'].max())
            largest_loss = float(df['profit'].min())

            # Advanced metrics
            consecutive_wins, consecutive_losses = trading_calc.calculate_consecutive_streaks(df['profit'])
            sharpe_ratio = trading_calc.calculate_sharpe_ratio(df['profit'])
            recovery_factor = trading_calc.calculate_recovery_factor(df['profit'])
            expectancy = trading_calc.calculate_expectancy(win_rate/100, avg_win, avg_loss)
            kelly_criterion = trading_calc.calculate_kelly_criterion(win_rate/100, avg_win, avg_loss)

            # Risk management metrics
            avg_position_size = float(df['volume'].mean()) if 'volume' in df.columns else 0
            total_volume = float(df['volume'].sum()) if 'volume' in df.columns else 0

            # Additional analytics
            avg_trade_duration = "N/A"  # Would calculate from duration data
            best_symbol = df.groupby('symbol')['profit'].sum().idxmax() if len(df['symbol'].unique()) > 0 else "N/A"
            worst_symbol = df.groupby('symbol')['profit'].sum().idxmin() if len(df['symbol'].unique()) > 0 else "N/A"

            return {
                'period': period,

                # Basic Metrics
                'total_trades': int(total_trades),
                'winning_trades': int(winning_trades),
                'losing_trades': int(losing_trades),
                'break_even_trades': int(break_even_trades),
                'net_profit': round(net_profit, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),

                # Performance Ratios
                'win_rate': round(win_rate, 2),
                'profit_factor': round(profit_factor, 2),
                'avg_profit': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_trade': round(avg_trade, 2),
                'avg_rr': round(avg_rr, 2),
                'median_rr': round(median_rr, 2),

                # Extreme Values
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2),
                'best_trade_pct': round((largest_win / float(df['account_balance'].iloc[0]) * 100), 2) if len(df) > 0 else 0,
                'worst_trade_pct': round((largest_loss / float(df['account_balance'].iloc[0]) * 100), 2) if len(df) > 0 else 0,

                # Advanced Analytics
                'consecutive_wins': int(consecutive_wins),
                'consecutive_losses': int(consecutive_losses),
                'sharpe_ratio': sharpe_ratio,
                'recovery_factor': recovery_factor,
                'expectancy': expectancy,
                'kelly_criterion': kelly_criterion,

                # Risk Management
                'avg_position_size': round(avg_position_size, 4),
                'total_volume': round(total_volume, 2),
                'risk_per_trade_avg': round(float(df['risk_per_trade'].mean()), 2) if 'risk_per_trade' in df.columns else 0,

                # Additional Insights
                'avg_trade_duration': avg_trade_duration,
                'best_symbol': best_symbol,
                'worst_symbol': worst_symbol,
                'total_symbols_traded': int(len(df['symbol'].unique())) if 'symbol' in df.columns else 0,

                # Template Required Fields
                'max_drawdown': trading_calc.calculate_max_drawdown(df['profit'].cumsum().tolist()) if len(df) > 0 else 0.0,
                'current_drawdown': 0.0,
                'risk_reward_ratio': avg_rr,
                'profit_loss_ratio': profit_factor,
                'starting_balance': float(df['account_balance'].iloc[0]) if len(df) > 0 else 0.0,
                'today_pnl': 0.0,
                'week_pnl': 0.0,
                'month_pnl': 0.0,
                'quarter_pnl': 0.0,
                'half_year_pnl': 0.0,
                'year_pnl': 0.0,
                'today_change': 0.0,
                'week_change': 0.0,
                'month_change': 0.0,
                'quarter_change': 0.0,
                'half_year_change': 0.0,
                'year_change': 0.0,
                'avg_risk_per_trade': round(float(df['risk_per_trade'].mean()), 2) if 'risk_per_trade' in df.columns else 0.0
            }

        except Exception as e:
            add_log('ERROR', f'Statistics generation error: {e}', 'Statistics')
            return create_empty_stats()

    @staticmethod
    def generate_performance_report(df, start_date, end_date):
        """Generate comprehensive performance report for date range"""
        try:
            if df.empty:
                return {}

            filtered_df = df[
                (df['exit_time'] >= start_date) &
                (df['exit_time'] <= end_date)
            ]

            return ProfessionalStatisticsGenerator.generate_trading_statistics(filtered_df, f"{start_date} to {end_date}")
        except Exception as e:
            add_log('ERROR', f'Performance report error: {e}', 'Statistics')
            return {}

# Initialize statistics generator
stats_generator = ProfessionalStatisticsGenerator()

# -----------------------------------------------------------------------------
# CALENDAR DASHBOARD SYSTEM (HYBRID VERSION)
# -----------------------------------------------------------------------------
class CalendarDashboard:
    """Advanced calendar system for daily PnL tracking with hybrid database support"""

    @staticmethod
    def update_daily_calendar(date=None):
        """Update or create daily calendar entry with comprehensive metrics"""
        if date is None:
            date = datetime.now().date()

        conn = db_manager.get_connection()
        try:
            # Database-specific date handling
            if conn.db_type == 'postgresql':
                date_query = "DATE(exit_time) = %s"
                date_param = date
            else:
                date_query = "date(exit_time) = date(?)"
                date_param = date.isoformat()  # SQLite needs string date

            query = f'''
                SELECT * FROM trades 
                WHERE status = 'CLOSED' 
                AND {date_query}
            '''
            
            # Execute query using hybrid manager
            trades = db_manager.execute_query(query, (date_param,))
            
            if not trades:
                # Create empty entry for the day
                if conn.db_type == 'postgresql':
                    insert_query = '''
                        INSERT INTO calendar_pnl 
                        (date, daily_pnl, closed_trades, winning_trades, losing_trades, break_even_trades, win_rate)
                        VALUES (%s, 0, 0, 0, 0, 0, 0)
                        ON CONFLICT (date) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                    '''
                else:
                    insert_query = '''
                        INSERT OR REPLACE INTO calendar_pnl 
                        (date, daily_pnl, closed_trades, winning_trades, losing_trades, break_even_trades, win_rate)
                        VALUES (?, 0, 0, 0, 0, 0, 0)
                    '''
                
                db_manager.execute_query(insert_query, (date,))
                return {'date': date, 'daily_pnl': 0, 'closed_trades': 0}

            # Calculate comprehensive daily metrics
            daily_pnl = float(sum(trade.get('profit', 0) for trade in trades))
            closed_trades = len(trades)
            winning_trades = len([t for t in trades if t.get('profit', 0) > 0])
            losing_trades = len([t for t in trades if t.get('profit', 0) < 0])
            break_even_trades = len([t for t in trades if t.get('profit', 0) == 0])
            
            # Calculate win rate
            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
            
            # Calculate average wins and losses
            winning_profits = [t.get('profit', 0) for t in trades if t.get('profit', 0) > 0]
            losing_profits = [t.get('profit', 0) for t in trades if t.get('profit', 0) < 0]
            
            avg_win = float(np.mean(winning_profits)) if winning_profits else 0
            avg_loss = float(np.mean(losing_profits)) if losing_profits else 0
            largest_win = float(max(winning_profits)) if winning_profits else 0
            largest_loss = float(min(losing_profits)) if losing_profits else 0
            
            # Calculate total volume
            total_volume = float(sum(trade.get('volume', 0) for trade in trades))

            # Update calendar entry with database-specific syntax
            if conn.db_type == 'postgresql':
                update_query = '''
                    INSERT INTO calendar_pnl 
                    (date, daily_pnl, closed_trades, winning_trades, losing_trades, break_even_trades, 
                     win_rate, avg_win, avg_loss, largest_win, largest_loss, total_volume, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (date) DO UPDATE SET
                        daily_pnl = EXCLUDED.daily_pnl,
                        closed_trades = EXCLUDED.closed_trades,
                        winning_trades = EXCLUDED.winning_trades,
                        losing_trades = EXCLUDED.losing_trades,
                        break_even_trades = EXCLUDED.break_even_trades,
                        win_rate = EXCLUDED.win_rate,
                        avg_win = EXCLUDED.avg_win,
                        avg_loss = EXCLUDED.avg_loss,
                        largest_win = EXCLUDED.largest_win,
                        largest_loss = EXCLUDED.largest_loss,
                        total_volume = EXCLUDED.total_volume,
                        updated_at = CURRENT_TIMESTAMP
                '''
            else:
                update_query = '''
                    INSERT OR REPLACE INTO calendar_pnl 
                    (date, daily_pnl, closed_trades, winning_trades, losing_trades, break_even_trades,
                     win_rate, avg_win, avg_loss, largest_win, largest_loss, total_volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                '''

            db_manager.execute_query(update_query, (
                date, daily_pnl, closed_trades, winning_trades, losing_trades, break_even_trades,
                win_rate, avg_win, avg_loss, largest_win, largest_loss, total_volume
            ))

            result = {
                'date': date,
                'daily_pnl': round(daily_pnl, 2),
                'closed_trades': closed_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'break_even_trades': break_even_trades,
                'win_rate': round(win_rate, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2),
                'total_volume': round(total_volume, 2)
            }

            add_log('INFO', f'Calendar updated for {date}: ${daily_pnl:.2f}', 'Calendar')
            return result

        except Exception as e:
            add_log('ERROR', f'Calendar update error for {date}: {e}', 'Calendar')
            return {'error': str(e)}
        finally:
            conn.close()

    @staticmethod
    def get_monthly_calendar(year, month):
        """Get comprehensive monthly calendar data with hybrid database support"""
        try:
            conn = db_manager.get_connection()

            # Get calendar data for the month
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"

            if conn.db_type == 'postgresql':
                query = '''
                    SELECT * FROM calendar_pnl 
                    WHERE date >= %s AND date < %s
                    ORDER BY date
                '''
            else:
                query = '''
                    SELECT * FROM calendar_pnl 
                    WHERE date >= ? AND date < ?
                    ORDER BY date
                '''

            calendar_df_data = db_manager.execute_query(query, (start_date, end_date))

            # Create complete calendar structure
            cal = calendar.Calendar()
            month_days = cal.monthdayscalendar(year, month)

            calendar_data = []
            for week in month_days:
                week_data = []
                for day in week:
                    if day == 0:
                        week_data.append(None)
                    else:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        
                        # Find day data
                        day_data = None
                        for cal_day in calendar_df_data:
                            if str(cal_day.get('date')) == date_str:
                                day_data = cal_day
                                break

                        if day_data:
                            week_data.append({
                                'day': day,
                                'pnl': day_data.get('daily_pnl', 0),
                                'trades': day_data.get('closed_trades', 0),
                                'win_rate': day_data.get('win_rate', 0),
                                'has_data': True
                            })
                        else:
                            week_data.append({
                                'day': day,
                                'pnl': 0,
                                'trades': 0,
                                'win_rate': 0,
                                'has_data': False
                            })
                calendar_data.append(week_data)

            # Calculate monthly summary
            if calendar_df_data:
                monthly_pnl = float(sum(day.get('daily_pnl', 0) for day in calendar_df_data))
                monthly_trades = int(sum(day.get('closed_trades', 0) for day in calendar_df_data))
                
                # Calculate average win rate (weighted by trades)
                total_weighted_win_rate = sum(day.get('win_rate', 0) * day.get('closed_trades', 0) for day in calendar_df_data)
                monthly_win_rate = total_weighted_win_rate / monthly_trades if monthly_trades > 0 else 0
                
                profitable_days = len([day for day in calendar_df_data if day.get('daily_pnl', 0) > 0])
                losing_days = len([day for day in calendar_df_data if day.get('daily_pnl', 0) < 0])
                break_even_days = len([day for day in calendar_df_data if day.get('daily_pnl', 0) == 0])
            else:
                monthly_pnl = 0
                monthly_trades = 0
                monthly_win_rate = 0
                profitable_days = 0
                losing_days = 0
                break_even_days = 0

            monthly_summary = {
                'total_pnl': round(monthly_pnl, 2),
                'total_trades': monthly_trades,
                'avg_win_rate': round(monthly_win_rate, 2),
                'profitable_days': profitable_days,
                'losing_days': losing_days,
                'break_even_days': break_even_days
            }

            return {
                'calendar': calendar_data,
                'monthly_summary': monthly_summary,
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month]
            }

        except Exception as e:
            add_log('ERROR', f'Monthly calendar error: {e}', 'Calendar')
            return {'error': str(e)}
        finally:
            conn.close()

# -----------------------------------------------------------------------------
# DATA STORAGE & SYNCHRONIZATION (HYBRID VERSION)
# -----------------------------------------------------------------------------
class ProfessionalDataStore:
    """Professional global data storage for real-time access"""
    def __init__(self):
        self.data_lock = threading.RLock()
        self.trades = []
        self.account_data = {}
        self.account_history = []
        self.open_positions = []
        self.calculated_stats = {}
        self.equity_curve = []
        self.calendar_data = {}
        self.initial_import_done = False
        self.last_update = None

global_data = ProfessionalDataStore()

class ProfessionalDataSynchronizer:
    """Professional MT5 data synchronization with hybrid database support"""

    def __init__(self):
        self.sync_lock = threading.Lock()
        self.last_sync = None
        # Use safe config access with defaults
        sync_config = config.get('sync', {})
        self.sync_interval = sync_config.get('auto_sync_interval', 300)
        self.days_history = sync_config.get('days_history', 90)

    def sync_with_mt5(self, force=False):
        """Synchronize data with MT5 with comprehensive error handling"""
        if not self.sync_lock.acquire(blocking=False) and not force:
            return False

        try:
            # Rate limiting
            if self.last_sync and (datetime.now() - self.last_sync).seconds < 30 and not force:
                return True

            add_log('INFO', 'Starting professional MT5 data synchronization...', 'Sync')

            # Get account data
            account_data = self.get_account_data()
            if not account_data:
                add_log('WARNING', 'Using demo account data - MT5 not connected', 'Sync')

            # Get trade history
            trades = self.get_trade_history(self.days_history)

            # Update database
            success = self.update_database_hybrid(trades, account_data)

            if success:
                # Update global data store
                with global_data.data_lock:
                    global_data.trades = trades
                    global_data.account_data = account_data
                    global_data.open_positions = [t for t in trades if t.get('status') == 'OPEN']
                    global_data.last_update = datetime.now()
                    global_data.initial_import_done = True

                # Update calendar
                calendar_dashboard.update_daily_calendar()

                self.last_sync = datetime.now()
                add_log('INFO', f'Professional sync completed: {len(trades)} trades', 'Sync')

                # Emit real-time update
                socketio.emit('data_updated', {
                    'timestamp': datetime.now().isoformat(),
                    'trades_count': len(trades),
                    'open_positions': len(global_data.open_positions)
                }, namespace='/realtime')

            return success

        except Exception as e:
            add_log('ERROR', f'Professional synchronization error: {e}', 'Sync')
            return False
        finally:
            try:
                self.sync_lock.release()
            except:
                pass

    def get_account_data(self):
        """Get current account data from MT5 with fallback"""
        if not MT5_AVAILABLE or not mt5_manager.connected:
            return self.get_demo_account_data()

        try:
            account_info = mt5.account_info()
            if account_info:
                return {
                    'balance': float(account_info.balance),
                    'equity': float(account_info.equity),
                    'margin': float(account_info.margin),
                    'free_margin': float(account_info.margin_free),
                    'leverage': int(account_info.leverage),
                    'currency': account_info.currency,
                    'server': account_info.server,
                    'login': account_info.login,
                    'name': getattr(account_info, 'name', 'Unknown'),
                    'company': getattr(account_info, 'company', 'Unknown')
                }
        except Exception as e:
            add_log('ERROR', f'Error getting account data: {e}', 'Sync')

        return self.get_demo_account_data()

    def get_demo_account_data(self):
        """Generate professional demo account data"""
        return {
            'balance': 25470.50,
            'equity': 26890.25,
            'margin': 3250.75,
            'free_margin': 23639.50,
            'leverage': 100,
            'currency': 'USD',
            'server': 'Professional-Demo',
            'login': 11146004,
            'name': 'Demo Trader',
            'company': 'Trading Professional'
        }

    def get_trade_history(self, days_back):
        """Get comprehensive trade history from MT5"""
        if not MT5_AVAILABLE or not mt5_manager.connected:
            return self.get_professional_demo_trades()

        try:
            from_date = datetime.now() - timedelta(days=days_back)
            to_date = datetime.now() + timedelta(days=1)

            # Get deals and positions
            deals = mt5.history_deals_get(from_date, to_date) or []
            positions = mt5.positions_get() or []

            trades = {}
            current_account_balance = mt5.account_info().balance if mt5_manager.connected else 10000

            # Process historical deals
            for deal in deals:
                try:
                    if deal.entry in [0, 1]:  # DEAL_ENTRY_IN or DEAL_ENTRY_OUT
                        trade = self.process_professional_deal(deal, current_account_balance)
                        if trade:
                            trades[deal.ticket] = trade
                except Exception as e:
                    add_log('ERROR', f'Error processing deal {deal.ticket}: {e}', 'Sync')
                    continue

            # Process open positions
            for position in positions:
                try:
                    trade = self.process_professional_position(position, current_account_balance)
                    if trade:
                        trades[position.ticket] = trade
                except Exception as e:
                    add_log('ERROR', f'Error processing position {position.ticket}: {e}', 'Sync')
                    continue

            trades_list = list(trades.values())
            trades_list.sort(key=lambda x: x.get('entry_time', datetime.min), reverse=True)
            return trades_list

        except Exception as e:
            add_log('ERROR', f'Error getting trade history: {e}', 'Sync')
            return self.get_professional_demo_trades()

    def process_professional_deal(self, deal, account_balance):
        """Process a deal into professional trade format"""
        try:
            trade_type = self.get_trade_type(deal.type)

            trade = {
                'ticket_id': deal.ticket,
                'symbol': deal.symbol,
                'type': trade_type,
                'volume': deal.volume,
                'entry_price': deal.price,
                'exit_price': deal.price,
                'profit': deal.profit,
                'commission': getattr(deal, 'commission', 0),
                'swap': getattr(deal, 'swap', 0),
                'comment': getattr(deal, 'comment', ''),
                'magic_number': getattr(deal, 'magic', 0),
                'entry_time': datetime.fromtimestamp(deal.time),
                'exit_time': datetime.fromtimestamp(deal.time),
                'status': 'CLOSED',
                'account_balance': account_balance,
                'account_equity': account_balance + deal.profit
            }

            # Calculate additional metrics
            trade = self.calculate_trade_metrics(trade)
            return trade

        except Exception as e:
            add_log('ERROR', f'Error processing deal {getattr(deal, "ticket", "unknown")}: {e}', 'Sync')
            return None

    def process_professional_position(self, position, account_balance):
        """Process a position into professional trade format"""
        try:
            trade_type = self.get_trade_type(position.type)
            current_price = getattr(position, 'price_current', position.price_open)
            floating_pnl = position.profit

            trade = {
                'ticket_id': position.ticket,
                'symbol': position.symbol,
                'type': trade_type,
                'volume': position.volume,
                'entry_price': position.price_open,
                'current_price': current_price,
                'sl_price': getattr(position, 'sl', 0),
                'tp_price': getattr(position, 'tp', 0),
                'profit': floating_pnl,
                'commission': 0,
                'swap': 0,
                'comment': getattr(position, 'comment', ''),
                'magic_number': getattr(position, 'magic', 0),
                'entry_time': datetime.fromtimestamp(position.time),
                'status': 'OPEN',
                'floating_pnl': floating_pnl,
                'account_balance': account_balance,
                'account_equity': account_balance + floating_pnl
            }

            # Calculate additional metrics
            trade = self.calculate_trade_metrics(trade)
            return trade

        except Exception as e:
            add_log('ERROR', f'Error processing position {getattr(position, "ticket", "unknown")}: {e}', 'Sync')
            return None

    def get_trade_type(self, mt5_type):
        """Convert MT5 trade type to readable format"""
        type_map = {
            0: 'BUY',
            1: 'SELL',
            2: 'BUY_LIMIT',
            3: 'SELL_LIMIT',
            4: 'BUY_STOP',
            5: 'SELL_STOP'
        }
        return type_map.get(mt5_type, 'UNKNOWN')

    def calculate_trade_metrics(self, trade):
        """Calculate professional trade metrics"""
        try:
            # Risk-reward ratio
            if trade.get('sl_price') and trade['sl_price'] > 0:
                trade['actual_rr'] = trading_calc.calculate_risk_reward(
                    trade['entry_price'],
                    trade.get('exit_price', trade.get('current_price', trade['entry_price'])),
                    trade['sl_price'],
                    trade['type']
                )
            else:
                trade['actual_rr'] = None

            # Trade duration
            if trade.get('exit_time'):
                trade['duration'] = trading_calc.calculate_trade_duration(
                    trade['entry_time'], trade['exit_time']
                )
            else:
                trade['duration'] = 'Active'

            # Account change percentage
            if trade.get('account_balance') and trade.get('account_equity'):
                trade['account_change_percent'] = trading_calc.calculate_account_change_percent(
                    trade['account_balance'], trade['account_equity']
                )
            else:
                trade['account_change_percent'] = 0

            # Risk per trade (simplified)
            if trade.get('account_balance'):
                trade['risk_per_trade'] = round(
                    abs(trade.get('profit', 0)) / trade['account_balance'] * 100, 2
                )
            else:
                trade['risk_per_trade'] = 0

        except Exception as e:
            add_log('ERROR', f'Error calculating trade metrics: {e}', 'Sync')

        return trade

    def get_professional_demo_trades(self):
        """Generate professional demo trades"""
        demo_trades = []
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US30', 'BTCUSD']
        base_time = datetime.now() - timedelta(days=60)
        base_balance = 10000

        for i in range(125):  # More demo trades
            symbol = symbols[i % len(symbols)]
            is_win = i % 3 != 0  # 66% win rate
            profit = np.random.uniform(50, 300) if is_win else np.random.uniform(-150, -30)
            volume = round(np.random.uniform(0.01, 1.0), 3)

            # Simulate account growth
            base_balance += profit * 0.1  # Small impact on base balance

            trade_type = 'BUY' if i % 2 == 0 else 'SELL'
            entry_time = base_time + timedelta(hours=i*12)
            exit_time = entry_time + timedelta(hours=np.random.randint(2, 72))

            trade = {
                'ticket_id': 500000 + i,
                'symbol': symbol,
                'type': trade_type,
                'volume': volume,
                'entry_price': round(np.random.uniform(1.0, 1.5), 5),
                'exit_price': round(np.random.uniform(1.0, 1.5), 5),
                'sl_price': round(np.random.uniform(0.995, 1.1), 5),
                'tp_price': round(np.random.uniform(1.1, 1.2), 5),
                'profit': round(profit, 2),
                'commission': round(np.random.uniform(2, 8), 2),
                'swap': round(np.random.uniform(-3, 3), 2),
                'comment': f'Professional trade #{i+1}',
                'magic_number': 12345,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'status': 'CLOSED',
                'account_balance': round(base_balance, 2),
                'account_equity': round(base_balance + profit, 2),
                'strategy': ['Breakout', 'Scalping', 'Swing', 'Position'][i % 4],
                'tags': ['High-Probability', 'News', 'Technical'][i % 3]
            }

            # Calculate advanced metrics
            trade = self.calculate_trade_metrics(trade)
            demo_trades.append(trade)

        # Add some open positions
        for i in range(8):
            symbol = symbols[i % len(symbols)]
            trade = {
                'ticket_id': 600000 + i,
                'symbol': symbol,
                'type': 'BUY' if i % 2 == 0 else 'SELL',
                'volume': round(np.random.uniform(0.1, 0.5), 2),
                'entry_price': round(np.random.uniform(1.0, 1.5), 5),
                'current_price': round(np.random.uniform(0.98, 1.52), 5),
                'sl_price': round(np.random.uniform(0.995, 1.1), 5),
                'tp_price': round(np.random.uniform(1.1, 1.2), 5),
                'profit': round(np.random.uniform(-50, 100), 2),
                'status': 'OPEN',
                'entry_time': datetime.now() - timedelta(hours=np.random.randint(1, 48)),
                'floating_pnl': round(np.random.uniform(-50, 100), 2),
                'account_balance': round(base_balance, 2),
                'account_equity': round(base_balance + np.random.uniform(-100, 200), 2),
                'strategy': ['Breakout', 'Scalping', 'Swing'][i % 3]
            }
            trade = self.calculate_trade_metrics(trade)
            demo_trades.append(trade)

        return demo_trades

    def update_database_hybrid(self, trades, account_data):
        """Update database with hybrid compatibility"""
        conn = db_manager.get_connection()
        
        try:
            # Start transaction with database-specific syntax
            if conn.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('BEGIN')
            else:
                cursor = conn.cursor()
                cursor.execute('BEGIN TRANSACTION')

            # Update trades with hybrid approach
            for trade in trades:
                self.insert_or_update_trade_hybrid(cursor, trade, account_data, conn.db_type)

            # Update account history with hybrid approach
            self.update_account_history_hybrid(cursor, account_data, conn.db_type)

            # Commit transaction
            conn.commit()
            add_log('INFO', f'Hybrid database update: {len(trades)} trades to {conn.db_type}', 'Database')
            return True

        except Exception as e:
            conn.rollback()
            add_log('ERROR', f'Hybrid database update error: {e}', 'Database')
            return False
        finally:
            conn.close()

    def insert_or_update_trade_hybrid(self, cursor, trade, account_data, db_type):
        """Professional trade insertion/update with hybrid compatibility"""
        try:
            # Prepare the values
            values = (
                trade.get('ticket_id'),
                trade.get('symbol'),
                trade.get('type'),
                safe_float_conversion(trade.get('volume')),
                safe_float_conversion(trade.get('entry_price')),
                safe_float_conversion(trade.get('current_price', trade.get('entry_price'))),
                safe_float_conversion(trade.get('exit_price')),
                safe_float_conversion(trade.get('sl_price')),
                safe_float_conversion(trade.get('tp_price')),
                trade.get('entry_time'),
                trade.get('exit_time'),
                safe_float_conversion(trade.get('profit')),
                safe_float_conversion(trade.get('commission')),
                safe_float_conversion(trade.get('swap')),
                trade.get('comment', ''),
                trade.get('magic_number', 0),
                trade.get('session', ''),
                safe_float_conversion(trade.get('planned_rr')),
                safe_float_conversion(trade.get('actual_rr')),
                trade.get('duration', ''),
                safe_float_conversion(trade.get('account_balance', account_data.get('balance', 0))),
                safe_float_conversion(trade.get('account_equity', account_data.get('equity', 0))),
                safe_float_conversion(trade.get('account_change_percent', 0)),
                trade.get('status', 'CLOSED'),
                safe_float_conversion(trade.get('floating_pnl', 0)),
                safe_float_conversion(trade.get('risk_per_trade', 0)),
                safe_float_conversion(trade.get('margin_used', 0)),
                trade.get('strategy', ''),
                trade.get('tags', '')
            )

            if db_type == 'postgresql':
                # PostgreSQL UPSERT syntax
                query = '''
                    INSERT INTO trades (
                        ticket_id, symbol, type, volume, entry_price, current_price, exit_price,
                        sl_price, tp_price, entry_time, exit_time, profit, commission, swap,
                        comment, magic_number, session, planned_rr, actual_rr, duration, 
                        account_balance, account_equity, account_change_percent, status, 
                        floating_pnl, risk_per_trade, margin_used, strategy, tags, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                             %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        type = EXCLUDED.type,
                        volume = EXCLUDED.volume,
                        entry_price = EXCLUDED.entry_price,
                        current_price = EXCLUDED.current_price,
                        exit_price = EXCLUDED.exit_price,
                        sl_price = EXCLUDED.sl_price,
                        tp_price = EXCLUDED.tp_price,
                        entry_time = EXCLUDED.entry_time,
                        exit_time = EXCLUDED.exit_time,
                        profit = EXCLUDED.profit,
                        commission = EXCLUDED.commission,
                        swap = EXCLUDED.swap,
                        comment = EXCLUDED.comment,
                        magic_number = EXCLUDED.magic_number,
                        session = EXCLUDED.session,
                        planned_rr = EXCLUDED.planned_rr,
                        actual_rr = EXCLUDED.actual_rr,
                        duration = EXCLUDED.duration,
                        account_balance = EXCLUDED.account_balance,
                        account_equity = EXCLUDED.account_equity,
                        account_change_percent = EXCLUDED.account_change_percent,
                        status = EXCLUDED.status,
                        floating_pnl = EXCLUDED.floating_pnl,
                        risk_per_trade = EXCLUDED.risk_per_trade,
                        margin_used = EXCLUDED.margin_used,
                        strategy = EXCLUDED.strategy,
                        tags = EXCLUDED.tags,
                        updated_at = CURRENT_TIMESTAMP
                '''
            else:
                # SQLite REPLACE syntax
                query = '''
                    INSERT OR REPLACE INTO trades (
                        ticket_id, symbol, type, volume, entry_price, current_price, exit_price,
                        sl_price, tp_price, entry_time, exit_time, profit, commission, swap,
                        comment, magic_number, session, planned_rr, actual_rr, duration, 
                        account_balance, account_equity, account_change_percent, status, 
                        floating_pnl, risk_per_trade, margin_used, strategy, tags, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                             ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                '''

            cursor.execute(query, values)

        except Exception as e:
            add_log('ERROR', f'Hybrid trade save error {trade.get("ticket_id")}: {e}', 'Database')

    def update_account_history_hybrid(self, cursor, account_data, db_type):
        """Update professional account history with hybrid compatibility"""
        try:
            values = (
                datetime.now(),
                account_data.get('balance', 0),
                account_data.get('equity', 0),
                account_data.get('margin', 0),
                account_data.get('free_margin', 0),
                account_data.get('leverage', 100),
                account_data.get('currency', 'USD'),
                account_data.get('server', 'MT5')
            )

            if db_type == 'postgresql':
                query = '''
                    INSERT INTO account_history 
                    (timestamp, balance, equity, margin, free_margin, leverage, currency, server)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                '''
            else:
                query = '''
                    INSERT INTO account_history 
                    (timestamp, balance, equity, margin, free_margin, leverage, currency, server)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''

            cursor.execute(query, values)
        except Exception as e:
            add_log('ERROR', f'Hybrid account history update error: {e}', 'Database')

# Initialize professional synchronizer
data_synchronizer = ProfessionalDataSynchronizer()

# -----------------------------------------------------------------------------
# AUTO-SYNC THREAD WITH PROFESSIONAL FEATURES
# -----------------------------------------------------------------------------
class ProfessionalAutoSyncThread(threading.Thread):
    """Professional background synchronization thread"""

    def __init__(self, interval=300):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True
        self.last_backup = None

    def run(self):
        add_log('INFO', f'Professional auto-sync started (interval: {self.interval}s)', 'AutoSync')

        while self.running:
            try:
                # Perform synchronization
                data_synchronizer.sync_with_mt5()

                # Daily backup at 2 AM
                now = datetime.now()
                if (self.last_backup is None or
                    (now.hour == 2 and now.minute < 5 and
                     (self.last_backup is None or self.last_backup.date() != now.date()))):
                    backup_database()
                    self.last_backup = now

            except Exception as e:
                add_log('ERROR', f'Auto-sync error: {e}', 'AutoSync')

            # Sleep with interruption check
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        self.running = False

# Start professional auto-sync
auto_sync_thread = ProfessionalAutoSyncThread(
    interval=config['sync'].get('auto_sync_interval', 300)
)
auto_sync_thread.start()


# -----------------------------------------------------------------------------
# FLASK-WTF FORMS
# -----------------------------------------------------------------------------
class ProfessionalLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()],
                           render_kw={"placeholder": "Enter your username", "class": "form-control"})
    password = PasswordField('Password', validators=[DataRequired()],
                             render_kw={"placeholder": "Enter your password", "class": "form-control"})


class TradePlanForm(FlaskForm):
    symbol = StringField('Symbol', validators=[DataRequired()],
                         render_kw={"placeholder": "e.g., EURUSD", "class": "form-control"})
    direction = SelectField('Direction', choices=[('LONG', 'Long'), ('SHORT', 'Short'), ('BOTH', 'Both')],
                            render_kw={"class": "form-control"})
    entry_price = FloatField('Entry Price', validators=[Optional()],
                             render_kw={"placeholder": "Optional", "class": "form-control"})
    stop_loss = FloatField('Stop Loss', validators=[Optional()],
                           render_kw={"placeholder": "Optional", "class": "form-control"})
    take_profit = FloatField('Take Profit', validators=[Optional()],
                             render_kw={"placeholder": "Optional", "class": "form-control"})
    confidence_level = SelectField('Confidence',
                                   choices=[(1, 'Low (1)'), (2, 'Medium-Low (2)'),
                                            (3, 'Medium (3)'), (4, 'High (4)'), (5, 'Very High (5)')],
                                   coerce=int, render_kw={"class": "form-control"})
    notes = TextAreaField('Analysis & Notes',
                          render_kw={"placeholder": "Enter your market analysis, setup conditions, and trade plan...",
                                     "rows": 6, "class": "form-control"})
    # === ADD NEW FIELDS HERE ===
    strategy = StringField('Strategy', validators=[DataRequired()],
                           render_kw={"placeholder": "e.g., Breakout, Pullback", "class": "form-control"})
    timeframe = SelectField('Timeframe',
                            choices=[('', 'Select Timeframe'),
                                     ('1M', '1 Minute'), ('5M', '5 Minutes'), ('15M', '15 Minutes'),
                                     ('30M', '30 Minutes'), ('1H', '1 Hour'), ('4H', '4 Hours'),
                                     ('Daily', 'Daily'), ('Weekly', 'Weekly')],
                            validators=[DataRequired()],
                            render_kw={"class": "form-control"})
    plan_date = StringField('Plan Date',
                            default=lambda: datetime.now().strftime('%Y-%m-%d'),
                            render_kw={"class": "form-control", "type": "date"})
    entry_condition = TextAreaField('Entry Conditions',
                                    render_kw={"placeholder": "Describe specific conditions for entry...",
                                               "rows": 3, "class": "form-control"})
    exit_condition = TextAreaField('Exit Conditions',
                                   render_kw={"placeholder": "Define exit strategy...",
                                              "rows": 3, "class": "form-control"})
    risk_percent = FloatField('Risk %', validators=[Optional()],
                              render_kw={"placeholder": "1.0", "class": "form-control", "step": "0.01"})
    reward_percent = FloatField('Reward %', validators=[Optional()],
                                render_kw={"placeholder": "2.0", "class": "form-control", "step": "0.01"})
    status = SelectField('Status',
                         choices=[('pending', 'Pending'), ('executed', 'Executed'), ('cancelled', 'Cancelled')],
                         default='pending',
                         render_kw={"class": "form-control"})
    outcome = SelectField('Outcome',
                          choices=[('', 'Select Outcome'), ('profit', 'Profit'), ('loss', 'Loss'),
                                   ('breakeven', 'Breakeven')],
                          validators=[Optional()],
                          render_kw={"class": "form-control"})


#  ======== DATABASE INITIALIZATION FUNCTION ========
# def init_trade_plans_table():
#     """Initialize or update trade_plans table with required columns"""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     try:
#         # Check if table exists
#         cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_plans'")
#         table_exists = cursor.fetchone()
#
#         if not table_exists:
#             # Create new table with CORRECT column names
#             cursor.execute('''
#                 CREATE TABLE trade_plans (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     symbol TEXT NOT NULL,
#                     strategy TEXT,
#                     timeframe TEXT,
#                     plan_date TEXT,
#                     entry_conditions TEXT,
#                     exit_conditions TEXT,
#                     risk_percent REAL,
#                     reward_percent REAL,
#                     status TEXT DEFAULT 'pending',
#                     outcome TEXT,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             ''')
#             print("✅ Created trade_plans table with correct columns")
#         else:
#             # Check and add missing columns with CORRECT names
#             cursor.execute("PRAGMA table_info(trade_plans)")
#             existing_columns = [column[1] for column in cursor.fetchall()]
#
#             # Required columns to add - CORRECT NAMES
#             columns_to_add = [
#                 ('strategy', 'TEXT'),
#                 ('timeframe', 'TEXT'),
#                 ('plan_date', 'TEXT'),
#                 ('entry_conditions', 'TEXT'),
#                 ('exit_conditions', 'TEXT'),
#                 ('risk_percent', 'REAL'),
#                 ('reward_percent', 'REAL'),
#                 ('status', 'TEXT DEFAULT "pending"'),
#                 ('outcome', 'TEXT')
#             ]
#
#             for column_name, column_type in columns_to_add:
#                 if column_name not in existing_columns:
#                     cursor.execute(f'ALTER TABLE trade_plans ADD COLUMN {column_name} {column_type}')
#                     print(f"✅ Added missing column: {column_name}")
#
#         conn.commit()
#         print("✅ Trade plans table initialization completed")
#
#     except Exception as e:
#         print(f"❌ Error initializing trade_plans table: {e}")
#         conn.rollback()
#     finally:
#         conn.close()
#
# # Initialize the table when app starts
# init_trade_plans_table()


'''
# ======== PROFESSIONAL POSTGRESQL INITIALIZATION ========
initialize_application()

# ======== EMERGENCY DATABASE RESET ========
def reset_trade_plans_table():
    """Reset trade_plans table for PostgreSQL or SQLite"""
    try:
        conn = get_db_connection()
        cursor = cursor_with_dict(conn)

        cursor.execute('DROP TABLE IF EXISTS trade_plans')

        if USE_POSTGRES:
            cursor.execute('''
                CREATE TABLE trade_plans (
                    id SERIAL PRIMARY KEY,
                    plan_date DATE NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    strategy VARCHAR(100),
                    timeframe VARCHAR(20),
                    entry_conditions TEXT,
                    exit_conditions TEXT,
                    risk_percent REAL,
                    reward_percent REAL,
                    status VARCHAR(20) DEFAULT 'pending',
                    outcome VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE trade_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT,
                    timeframe TEXT,
                    entry_conditions TEXT,
                    exit_conditions TEXT,
                    risk_percent REAL,
                    reward_percent REAL,
                    status TEXT DEFAULT 'pending',
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Trade plans table reset successfully!")

    except Exception as e:
        print(f"❌ Error resetting trade plans table: {e}")


# =============================================================================
# LICENSE VALIDATION MIDDLEWARE
# =============================================================================

@app.before_request
def check_license():
    """Check license status before each request"""
    # Skip license check for certain routes
    exempt_routes = ['static', 'login', 'register', 'logout', 'api_validate_license']
    
    if request.endpoint in exempt_routes:
        return
    
    # Check license status
    is_valid, message = license_manager.validate_license()
    
    if not is_valid:
        # Allow access to license management page even if expired
        if request.endpoint not in ['license_management', 'api_license_status', 'api_activate_license']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'error': 'License required',
                    'message': message,
                    'redirect': url_for('license_management')
                }), 402  # Payment Required
            else:
                flash(f'⚠️ {message}. Please activate your license.', 'warning')
                return redirect(url_for('license_management'))
# =============================================================================
# DESKTOP APP CONFIGURATION
# =============================================================================

def setup_desktop_environment():
    """Setup desktop-specific environment"""
    if detect_environment() == 'sqlite':
        # Create necessary desktop directories
        desktop_dirs = [
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'exports'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'backups'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'reports')
        ]
        
        for directory in desktop_dirs:
            os.makedirs(directory, exist_ok=True)
        
        # Set desktop-specific configurations
        config.setdefault('desktop', {})
        config['desktop'].update({
            'auto_start': False,
            'minimize_to_tray': True,
            'start_with_windows': False,
            'export_directory': desktop_dirs[0],
            'backup_directory': desktop_dirs[1]
        })
        
        print("✅ Desktop environment configured")

# Call setup during initialization
setup_desktop_environment()

# =============================================================================
# CROSS-PLATFORM UTILITIES
# =============================================================================

def get_platform_specific_config():
    """Get platform-specific configuration"""
    system = platform.system().lower()
    
    config = {
        'windows': {
            'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
            'data_dir': os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal'),
            'backup_dir': os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'MT5Journal', 'backups')
        },
        'darwin': {  # macOS
            'terminal_path': '/Applications/MetaTrader 5.app/Contents/MacOS/terminal64',
            'data_dir': os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MT5Journal'),
            'backup_dir': os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'backups')
        },
        'linux': {
            'terminal_path': '/usr/bin/mt5',
            'data_dir': os.path.join(os.path.expanduser('~'), '.mt5journal'),
            'backup_dir': os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'backups')
        }
    }
    
    return config.get(system, config['windows'])  # Default to Windows

def setup_auto_start():
    """Setup auto-start based on platform"""
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            setup_windows_auto_start()
        elif system == 'darwin':
            setup_macos_auto_start()
        elif system == 'linux':
            setup_linux_auto_start()
    except Exception as e:
        add_log('ERROR', f'Auto-start setup failed: {e}', 'Desktop')

def setup_windows_auto_start():
    """Setup Windows auto-start"""
    if config.get('desktop', {}).get('start_with_windows'):
        try:
            import winreg
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                app_path = os.path.abspath(sys.executable)
                winreg.SetValueEx(reg_key, "MT5Journal", 0, winreg.REG_SZ, app_path)
                
            add_log('INFO', 'Windows auto-start configured', 'Desktop')
        except Exception as e:
            add_log('ERROR', f'Windows auto-start failed: {e}', 'Desktop')

# =============================================================================
# SYNC API ROUTES
# =============================================================================

@app.route('/api/sync_now')
@login_required
def api_sync_now():
@hybrid_compatible 
    """Professional manual sync API"""
    try:
        print("🔄 Manual sync requested via API")
        success = data_synchronizer.sync_with_mt5(force=True)

        if success:
            # Get updated stats - FIXED: Convert int64 to regular int
            conn = get_db_connection()
            trades_count = int(pd.read_sql('SELECT COUNT(*) as count FROM trades', conn).iloc[0]['count'])
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Sync completed! Imported {trades_count} trades.',
                'trades_count': trades_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Sync failed. Check MT5 connection.'
            })

    except Exception as e:
        print(f"❌ Sync error: {e}")
        return jsonify({
            'success': False,
            'message': f'Sync error: {str(e)}'
        })


@app.route('/api/sync_status')
@login_required
def api_sync_status():
@hybrid_compatible 
    """Get current sync status"""
    try:
        conn = get_db_connection()
        # FIXED: Convert int64 to regular int
        trades_count = int(pd.read_sql('SELECT COUNT(*) as count FROM trades', conn).iloc[0]['count'])
        open_positions = int(
            pd.read_sql('SELECT COUNT(*) as count FROM trades WHERE status = "OPEN"', conn).iloc[0]['count'])
        conn.close()

        return jsonify({
            'trades_total': trades_count,
            'open_positions': open_positions,
            'last_sync': data_synchronizer.last_sync.isoformat() if data_synchronizer.last_sync else None,
            'mt5_connected': mt5_manager.connected
        })
    except Exception as e:
        return jsonify({'error': str(e)})
    

# ======== ROUTES START HERE ========
# -----------------------------------------------------------------------------
# FLASK ROUTES - PROFESSIONAL IMPLEMENTATION
# -----------------------------------------------------------------------------
@app.context_processor
def inject_hybrid_data():
    """Inject hybrid-specific data into all templates"""
    environment = detect_environment()
    is_demo_mode = not mt5_manager.connected
    
    # Get license information (if license manager exists)
    try:
        license_info = license_manager.get_license_info()
    except:
        # Fallback if license manager not available
        license_info = {
            'status': 'free',
            'is_valid': True,
            'trial_days_left': None,
            'features': ['full_trading_journal', 'advanced_analytics', 'ai_coaching', 'risk_analysis'],
            'message': 'Free Version - All Features Included'
        }
    
    return {
        # KEEP ALL EXISTING VARIABLES (Backward Compatibility)
        'current_time': datetime.now().strftime('%H:%M:%S'),
        'current_date': datetime.now().strftime('%Y-%m-%d'),
        'app_name': 'Professional MT5 Journal',
        'app_version': '2.0.0',
        'mt5_connected': mt5_manager.connected,
        'demo_mode': is_demo_mode,
        
        # ADD NEW HYBRID VARIABLES (Automatic Injection)
        'environment': environment,
        'is_web': environment == 'postgresql',
        'is_desktop': environment == 'sqlite',
        'db_type': environment,
        'is_postgresql': environment == 'postgresql',
        'is_sqlite': environment == 'sqlite',
        'mt5_available': MT5_AVAILABLE,
        'hybrid_mode': True,
        'current_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_year': datetime.now().year,
        'current_month': datetime.now().month,
        'current_month_name': datetime.now().strftime('%B'),
        
        # ADDED: Enhanced status variables
        'connection_attempts': mt5_manager.connection_attempts,
        'last_connection': mt5_manager.last_connection,
        
        # ADDED: Helper functions for templates (optional)
        'format_currency': lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else "$0.00",
        'format_percent': lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else "0.00%",
        'is_profitable': lambda pnl: pnl > 0 if isinstance(pnl, (int, float)) else False,
        
        # ADD LICENSE INFORMATION (New Addition)
        'license_status': license_info['status'],
        'license_valid': license_info['is_valid'],
        'trial_days_left': license_info['trial_days_left'],
        'license_features': license_info['features'],
        'license_message': license_info['message'],
        'is_premium': license_info['status'] == 'licensed' or license_info['status'] == 'free'
    }

# ... your other routes continue below EXACTLY AS THEY ARE ...
@app.route('/')
def index():
    """Professional home page"""
    if current_user.is_authenticated:
        return redirect(url_for('professional_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Professional login page"""
    if current_user.is_authenticated:
        return redirect(url_for('professional_dashboard'))

    form = ProfessionalLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.get_by_username(username)
        if user is None:
            # Auto-create user for demo (professional feature)
            user = User.create(username, password)
            if user:
                add_log('INFO', f'Auto-created professional user: {username}', 'Auth')
                flash('Account created successfully!', 'success')

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.update_last_login()
            add_log('INFO', f'Professional user logged in: {username}', 'Auth')

            # Initial professional sync
            threading.Thread(target=data_synchronizer.sync_with_mt5, daemon=True).start()

            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('professional_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Professional registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('professional_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')

        existing_user = User.get_by_username(username)
        if existing_user:
            flash('Username already exists', 'warning')
            return render_template('register.html')

        user = User.create(username, password, email)
        if user:
            login_user(user)
            add_log('INFO', f'New professional user registered: {username}', 'Auth')
            flash('Registration successful! Welcome to Professional MT5 Journal.', 'success')
            return redirect(url_for('professional_dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Professional logout"""
    username = current_user.username
    logout_user()
    add_log('INFO', f'User logged out: {username}', 'Auth')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# =============================================================================
# FIXED PROFESSIONAL DASHBOARD ROUTE
# =============================================================================
@app.route('/dashboard')
@login_required
@hybrid_compatible
def professional_dashboard():
    """Enhanced professional dashboard with safe dictionary handling"""
    try:
        conn = get_db_connection()

        # Get comprehensive statistics
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
        stats = stats_generator.generate_trading_statistics(df) if not df.empty else create_empty_stats()

        # Get account data
        account_data = data_synchronizer.get_account_data()

        # Get current month calendar
        now = datetime.now()
        calendar_data = calendar_dashboard.get_monthly_calendar(now.year, now.month)

        # Get recent trades for dashboard
        recent_trades = pd.read_sql(
            'SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10', conn
        ).to_dict('records') if not df.empty else []

        # Get open positions
        open_positions = pd.read_sql(
            'SELECT * FROM trades WHERE status = "OPEN" ORDER BY entry_time DESC', conn
        ).to_dict('records')

    except Exception as e:
        add_log('ERROR', f'Dashboard error: {e}', 'Dashboard')
        stats, account_data, calendar_data, recent_trades, open_positions = create_empty_stats(), {}, {}, [], []
    finally:
        conn.close()

    return render_template('dashboard.html',
                         stats=stats,
                         account_data=account_data,
                         calendar_data=calendar_data,
                         recent_trades=recent_trades,
                         open_positions=open_positions,
                         current_year=datetime.now().year,
                         current_month=datetime.now().month)


# =============================================================================
# COMPREHENSIVE STATISTICS DASHBOARD ROUTE
# =============================================================================

# =============================================================================
# HYBRID-UPGRADED STATISTICS DASHBOARD ROUTE
# =============================================================================

@app.route('/statistics')
@login_required
def statistics_dashboard():
@hybrid_compatible 
    """Main statistics dashboard - HYBRID COMPATIBLE VERSION"""
    period = request.args.get('period', 'monthly')

    conn = get_universal_connection()  # CHANGED: Use universal connection
    try:
        # Get filtered data using existing functions
        df = get_trades_by_period(conn, period)

        # Use EXISTING stats generator (already in your app.py)
        stats = stats_generator.generate_trading_statistics(df, period.capitalize())

        # Get additional data using existing calendar system
        symbol_stats = calculate_symbol_performance(df)
        strategy_stats = calculate_strategy_performance(df)
        calendar_data = calendar_dashboard.get_monthly_calendar(
            datetime.now().year,
            datetime.now().month
        )

        return render_template('statistics/executive_dashboard.html',
                               stats=stats,
                               symbol_stats=symbol_stats,
                               strategy_stats=strategy_stats,
                               calendar_data=calendar_data,
                               current_period=period)

    except Exception as e:
        add_log('ERROR', f'Statistics dashboard error: {e}', 'Statistics')
        return render_template('statistics/executive_dashboard.html',
                               stats=create_empty_stats(),
                               symbol_stats=[],
                               strategy_stats=[],
                               calendar_data={},
                               current_period=period)
    finally:
        conn.close()


def get_trades_by_period(conn, period):
    """Get trades filtered by time period - HYBRID COMPATIBLE VERSION"""
    end_date = datetime.now()

    if period == 'daily':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        start_date = end_date - timedelta(days=end_date.weekday())
    elif period == 'monthly':
        start_date = end_date.replace(day=1)
    elif period == '3months':
        start_date = end_date - timedelta(days=90)
    elif period == '6months':
        start_date = end_date - timedelta(days=180)
    elif period == '1year':
        start_date = end_date - timedelta(days=365)
    else:
        # CHANGED: Use hybrid dataframe fetch for "All time"
        return conn_fetch_dataframe(conn, 'SELECT * FROM trades')

    # CHANGED: Use hybrid dataframe fetch with parameters
    query = 'SELECT * FROM trades WHERE entry_time >= ?'
    return conn_fetch_dataframe(conn, query, params=(start_date,))


def calculate_symbol_performance(df):
    """Calculate symbol performance using existing metrics"""
    if df.empty:
        return []

    symbol_stats = []
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]

        symbol_stats.append({
            'symbol': symbol,
            'trade_count': len(symbol_df),
            'win_rate': len(symbol_df[symbol_df['profit'] > 0]) / len(symbol_df) * 100,
            'net_pnl': symbol_df['profit'].sum(),
            'avg_pnl': symbol_df['profit'].mean(),
            'best_trade': symbol_df['profit'].max(),
            'worst_trade': symbol_df['profit'].min(),
            'total_volume': symbol_df['volume'].sum() if 'volume' in symbol_df.columns else 0
        })

    return sorted(symbol_stats, key=lambda x: x['net_pnl'], reverse=True)


def calculate_strategy_performance(df):
    """Calculate strategy performance using existing analytics"""
    if df.empty or 'strategy' not in df.columns:
        return []

    strategy_stats = []
    for strategy in df['strategy'].unique():
        if pd.isna(strategy) or strategy == '':
            continue

        strategy_df = df[df['strategy'] == strategy]
        winning_trades = len(strategy_df[strategy_df['profit'] > 0])
        total_trades = len(strategy_df)

        strategy_stats.append({
            'name': strategy,
            'trade_count': total_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'net_pnl': strategy_df['profit'].sum(),
            'profit_factor': (strategy_df[strategy_df['profit'] > 0]['profit'].sum() /
                              abs(strategy_df[strategy_df['profit'] < 0]['profit'].sum()))
            if len(strategy_df[strategy_df['profit'] < 0]) > 0 else float('inf'),
            'avg_rr': strategy_df['actual_rr'].mean() if 'actual_rr' in strategy_df.columns else 0
        })

    return sorted(strategy_stats, key=lambda x: x['net_pnl'], reverse=True)


# =============================================================================
# HYBRID-UPGRADED JOURNAL ROUTE
# =============================================================================

@app.route('/journal')
@login_required
def journal():
@hybrid_compatible 
    """Professional trade journal with advanced calculations - HYBRID COMPATIBLE VERSION"""
    conn = get_universal_connection()  # CHANGED: Use universal connection
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page

        # Get filter parameters
        symbol_filter = request.args.get('symbol', '')
        status_filter = request.args.get('status', '')

        # Build query
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []

        if symbol_filter:
            query += ' AND symbol = ?'
            params.append(symbol_filter)

        if status_filter:
            query += ' AND status = ?'
            params.append(status_filter)

        query += ' ORDER BY entry_time DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])

        # CHANGED: Use hybrid dataframe fetch
        trades = conn_fetch_dataframe(conn, query, params=params)
        trades_dict = trades.to_dict('records') if not trades.empty else []

        # ADD: Convert string dates to datetime objects
        trades_dict = convert_trade_dates(trades_dict)

        # Get unique symbols for filter dropdown - CHANGED: Use hybrid dataframe fetch
        symbols = conn_fetch_dataframe(conn, 'SELECT DISTINCT symbol FROM trades ORDER BY symbol')
        symbols_list = symbols['symbol'].tolist() if not symbols.empty else []

        # Get total count for pagination - CHANGED: Use universal fetch for count
        count_query = 'SELECT COUNT(*) as total FROM trades WHERE 1=1'
        count_params = []

        if symbol_filter:
            count_query += ' AND symbol = ?'
            count_params.append(symbol_filter)

        if status_filter:
            count_query += ' AND status = ?'
            count_params.append(status_filter)

        cursor = conn.cursor()
        universal_execute(cursor, count_query, count_params)
        total_count = cursor.fetchone()[0]

        # ADD: Calculate professional statistics - WITH ERROR HANDLING - CHANGED: Use hybrid dataframe fetch
        df_all_trades = conn_fetch_dataframe(conn, 'SELECT * FROM trades WHERE status = "CLOSED"')

        # SAFE STATS GENERATION - FIX FOR max_drawdown ERROR
        if not df_all_trades.empty:
            try:
                stats = stats_generator.generate_trading_statistics(df_all_trades)
                # Ensure all required stats fields exist
                required_stats = ['max_drawdown', 'win_rate', 'profit_factor', 'total_trades',
                                  'gross_profit', 'gross_loss', 'sharpe_ratio', 'avg_win',
                                  'avg_loss', 'largest_win', 'largest_loss', 'current_drawdown',
                                  'expectancy', 'risk_reward_ratio']

                # Convert stats to dict if it's an object
                if not isinstance(stats, dict):
                    stats_dict = {}
                    for field in required_stats:
                        stats_dict[field] = getattr(stats, field, 0.0)
                    stats = stats_dict
                else:
                    # Ensure all fields exist in dict
                    for field in required_stats:
                        if field not in stats:
                            stats[field] = 0.0
            except Exception as stats_error:
                add_log('ERROR', f'Stats calculation error: {stats_error}', 'Journal')
                stats = create_empty_stats()
        else:
            stats = create_empty_stats()

        # ADD: Calculate floating P&L from open positions - CHANGED: Use hybrid dataframe fetch
        open_positions = conn_fetch_dataframe(conn, 'SELECT * FROM trades WHERE status = "OPEN"')
        floating_pnl = open_positions['floating_pnl'].sum() if not open_positions.empty else 0

        # ADD: Calculate additional metrics for template - FIXED: Return lists not counts
        open_positions_data = open_positions.to_dict('records') if not open_positions.empty else []
        closed_trades_data = df_all_trades.to_dict('records') if not df_all_trades.empty else []

        # Calculate counts for display (optional)
        open_positions_count = len(open_positions_data)
        closed_trades_count = len(closed_trades_data)

    except Exception as e:
        add_log('ERROR', f'Journal error: {e}', 'Journal')
        trades_dict, symbols_list, total_count = [], [], 0
        stats = create_empty_stats()
        floating_pnl = 0
        open_positions_data = []  # FIXED: Use list instead of count
        closed_trades_data = []  # FIXED: Use list instead of count
        open_positions_count = 0
        closed_trades_count = 0
    finally:
        conn.close()

    # ADD: Template context with ALL required variables - FIXED variable names
    return render_template('journal.html',
                           trades=trades_dict,
                           symbols=symbols_list,
                           current_page=page,
                           total_pages=(total_count + per_page - 1) // per_page,
                           symbol_filter=symbol_filter,
                           status_filter=status_filter,
                           stats=stats,  # Professional statistics
                           floating_pnl=floating_pnl,  # Real-time P&L
                           open_positions=open_positions_data,  # FIXED: List for template
                           closed_trades=closed_trades_data,  # FIXED: List for template
                           open_positions_count=open_positions_count,  # Count for display
                           closed_trades_count=closed_trades_count,  # Count for display
                           mt5_connected=mt5_manager.connected,  # MT5 status
                           current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
                           # Template calculation functions
                           calculate_planned_rr=calculate_planned_rr,
                           calculate_actual_rr=calculate_actual_rr,
                           calculate_trade_duration=calculate_trade_duration,
                           calculate_pnl_percent=calculate_pnl_percent,
                           calculate_account_change=calculate_account_change,
                           get_trade_status=get_trade_status)


# =============================================================================
# ORIGINAL HELPER FUNCTIONS (UNCHANGED - MAINTAINED EXACTLY AS PROVIDED)
# =============================================================================

def create_empty_stats():
    """Create empty statistics with all required fields"""
    return {
        'max_drawdown': 0.0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'total_trades': 0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'sharpe_ratio': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'largest_win': 0.0,
        'largest_loss': 0.0,
        'current_drawdown': 0.0,
        'expectancy': 0.0,
        'risk_reward_ratio': 0.0
    }


def calculate_planned_rr(trade):
    """Calculate planned risk/reward ratio"""
    try:
        if trade.get('planned_rr'):
            return float(trade['planned_rr'])
        return None
    except:
        return None


def calculate_actual_rr(trade):
    """Calculate actual risk/reward ratio"""
    try:
        if trade.get('actual_rr'):
            return float(trade['actual_rr'])
        return None
    except:
        return None


def calculate_trade_duration(trade):
    """Calculate trade duration"""
    try:
        if trade.get('duration'):
            return trade['duration']
        return None
    except:
        return None


def calculate_pnl_percent(trade):
    """Calculate P/L percentage"""
    try:
        if trade.get('profit') and trade.get('account_balance'):
            return (float(trade['profit']) / float(trade['account_balance'])) * 100
        return 0.0
    except:
        return 0.0


def calculate_account_change(trade, trades, index):
    """Calculate account change percentage"""
    try:
        if trade.get('account_change_percent'):
            return float(trade['account_change_percent'])
        return 0.0
    except:
        return 0.0


def get_trade_status(trade):
    """Get trade status"""
    try:
        return trade.get('status', 'UNKNOWN')
    except:
        return 'UNKNOWN'
        
# ======== ADD NEW TRADE COMMENT/DUPLICATE ROUTES RIGHT HERE ========
# ======== PSYCHOLOGY LOG ROUTES ========

@app.route('/psychology_log')
@login_required
def psychology_log():
@hybrid_compatible 
    """Trading Psychology Log Dashboard"""
    # Create psychology logs table if it doesn't exist
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS psychology_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            trade_id TEXT,
            log_date DATETIME,
            emotion_level INTEGER,
            emotion_label TEXT,
            confidence_level INTEGER,
            stress_level INTEGER,
            discipline_level INTEGER,
            thoughts TEXT,
            improvement_areas TEXT,
            psychology_factors TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

    return render_template('psychology_log.html')


@app.route('/api/psychology_logs', methods=['GET', 'POST'])
@login_required
def psychology_logs_api():
@hybrid_compatible 
    """Psychology Logs API endpoint - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()  # CHANGED: Use universal connection
        cursor = conn.cursor()

        if request.method == 'POST':
            # Save new psychology log - CHANGED: Use universal_execute
            data = request.get_json()

            universal_execute(cursor, '''
                INSERT INTO psychology_logs 
                (user_id, trade_id, log_date, emotion_level, emotion_label, 
                 confidence_level, stress_level, discipline_level, thoughts, 
                 improvement_areas, psychology_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data.get('trade_id'),
                data.get('log_date'),
                data.get('emotion_level'),
                data.get('emotion_label'),
                data.get('confidence_level'),
                data.get('stress_level'),
                data.get('discipline_level'),
                data.get('thoughts'),
                data.get('improvement_areas'),
                json.dumps(data.get('psychology_factors', []))
            ))

            conn.commit()
            add_log('INFO', f'Psychology log saved for trade {data.get("trade_id")}', 'Psychology')

            return jsonify(success=True, message='Psychology log saved successfully')

        else:
            # Get psychology logs for current user - CHANGED: Use universal_execute
            universal_execute(cursor, '''
                SELECT * FROM psychology_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            ''', (current_user.id,))

            logs = cursor.fetchall()

            # Convert to dictionary format - ALL ORIGINAL LOGIC PRESERVED
            logs_dict = []
            for log in logs:
                logs_dict.append({
                    'id': log[0],
                    'trade_id': log[2],
                    'log_date': log[3],
                    'emotion_level': log[4],
                    'emotion_label': log[5],
                    'confidence_level': log[6],
                    'stress_level': log[7],
                    'discipline_level': log[8],
                    'thoughts': log[9],
                    'improvement_areas': log[10],
                    'psychology_factors': json.loads(log[11]) if log[11] else [],
                    'created_at': log[12]
                })

            return jsonify(logs=logs_dict)

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Psychology logs error: {e}', 'Psychology')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


@app.route('/api/psychology_stats')
@login_required
def psychology_stats():
@hybrid_compatible 
    """Psychology Statistics API - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()  # CHANGED: Use universal connection
        cursor = conn.cursor()

        # Get emotion distribution - CHANGED: Use universal_execute
        universal_execute(cursor, '''
            SELECT emotion_label, COUNT(*) as count 
            FROM psychology_logs 
            WHERE user_id = ? 
            GROUP BY emotion_label
        ''', (current_user.id,))

        emotion_stats = cursor.fetchall()

        # Get average metrics - CHANGED: Use universal_execute
        universal_execute(cursor, '''
            SELECT 
                AVG(confidence_level) as avg_confidence,
                AVG(stress_level) as avg_stress, 
                AVG(discipline_level) as avg_discipline
            FROM psychology_logs 
            WHERE user_id = ?
        ''', (current_user.id,))

        avg_metrics = cursor.fetchone()

        # ALL ORIGINAL CALCULATIONS AND LOGIC PRESERVED
        return jsonify({
            'emotion_distribution': dict(emotion_stats),
            'average_metrics': {
                'confidence': round(avg_metrics[0] or 0, 1),
                'stress': round(avg_metrics[1] or 0, 1),
                'discipline': round(avg_metrics[2] or 0, 1)
            }
        })

    except Exception as e:
        add_log('ERROR', f'Psychology stats error: {e}', 'Psychology')
        return jsonify(error=str(e)), 500
    finally:
        conn.close()


# ======== QUICK ACTION ROUTES ========
@app.route('/quick/journal')
@login_required
def quick_journal():
    """Quick journal access"""
    return redirect(url_for('journal'))


@app.route('/quick/trade_plan')
@login_required
def quick_trade_plan():
    """Quick trade plan access"""
    return redirect(url_for('trade_plan'))
        
# ======== UPDATE TRADE COMMENT ROUTE ========
@app.route('/api/update_trade_comment/<ticket_id>', methods=['POST'])
@login_required
def update_trade_comment(ticket_id):
    """Update trade comment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data = request.get_json()
        comment = data.get('comment', '')

        cursor.execute('''
            UPDATE trades SET comment = ? WHERE ticket_id = ?
        ''', (comment, ticket_id))

        conn.commit()
        add_log('INFO', f'Trade {ticket_id} comment updated', 'TradeJournal')

        return jsonify(success=True, message='Comment updated successfully')

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade comment update error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ======== EDIT TRADE DETAILS ROUTE ========
@app.route('/api/edit_trade/<ticket_id>', methods=['POST'])
@login_required
def edit_trade(ticket_id):
    """Edit trade details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data = request.get_json()

        # Update trade fields
        cursor.execute('''
            UPDATE trades SET 
                symbol = ?, type = ?, volume = ?, entry_price = ?,
                sl_price = ?, tp_price = ?, strategy = ?, comment = ?
            WHERE ticket_id = ?
        ''', (
            data.get('symbol'),
            data.get('type'),
            data.get('volume'),
            data.get('entry_price'),
            data.get('sl_price'),
            data.get('tp_price'),
            data.get('strategy'),
            data.get('comment'),
            ticket_id
        ))

        conn.commit()
        add_log('INFO', f'Trade {ticket_id} details updated', 'TradeJournal')

        return jsonify(success=True, message='Trade updated successfully')

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade edit error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ======== DUPLICATE TRADE ROUTE ========
@app.route('/api/duplicate_trade/<ticket_id>', methods=['POST'])
@login_required
def duplicate_trade(ticket_id):
    """Duplicate an existing trade"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get original trade data
        cursor.execute('''
            SELECT symbol, type, volume, entry_price, sl_price, tp_price, strategy, comment
            FROM trades WHERE ticket_id = ?
        ''', (ticket_id,))

        trade = cursor.fetchone()

        if trade:
            # Insert as new trade with current timestamp
            cursor.execute('''
                INSERT INTO trades 
                (ticket_id, symbol, type, volume, entry_price, sl_price, tp_price, 
                 strategy, comment, entry_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN', CURRENT_TIMESTAMP)
            ''', (
                f"DUPLICATE_{int(time.time())}",  # New ticket ID
                trade[0],  # symbol
                trade[1],  # type
                trade[2],  # volume
                trade[3],  # entry_price
                trade[4],  # sl_price
                trade[5],  # tp_price
                trade[6],  # strategy
                f"Duplicate of {ticket_id} - {trade[7]}"  # comment
            ))

            conn.commit()
            add_log('INFO', f'Trade {ticket_id} duplicated', 'TradeJournal')

            return jsonify(success=True, message='Trade duplicated successfully')
        else:
            return jsonify(success=False, message='Original trade not found'), 404

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade duplicate error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()

# ... your existing trade_plan code (line 2530) ...

# ======== DELETE ROUTE FIRST (MUST COME BEFORE TRADE_PLAN) ========

# ======== TRADE PLAN MAIN ROUTE ========
@app.route('/trade_plan', methods=['GET', 'POST'])
@login_required
def trade_plan():
    """Professional trade planning - HYBRID COMPATIBLE VERSION"""
    form = TradePlanForm()

    if request.method == 'POST':
        try:
            conn = get_universal_connection()  # CHANGED: Use universal connection
            cursor = conn.cursor()

            # Get data from HTML form fields
            symbol = request.form.get('symbol', '').upper()
            strategy = request.form.get('strategy', '')
            timeframe = request.form.get('timeframe', '')
            plan_date = request.form.get('plan_date', datetime.now().date())
            entry_conditions = request.form.get('entry_conditions', '')
            exit_conditions = request.form.get('exit_conditions', '')
            risk_percent = request.form.get('risk_percent')
            reward_percent = request.form.get('reward_percent')
            status = request.form.get('status', 'pending')
            outcome = request.form.get('outcome', '')

            # Insert into database with PROPER field names - CHANGED: Use universal_execute
            universal_execute(cursor, '''
                INSERT INTO trade_plans 
                (plan_date, symbol, strategy, timeframe, entry_conditions, exit_conditions, 
                 risk_percent, reward_percent, status, outcome, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                plan_date,
                symbol,
                strategy,
                timeframe,
                entry_conditions,
                exit_conditions,
                risk_percent,
                reward_percent,
                status,
                outcome if outcome else None
            ))

            conn.commit()
            flash('✅ Trade plan saved successfully!', 'success')
            add_log('INFO', f'New trade plan created for {symbol}', 'TradePlan')

            return redirect(url_for('trade_plan'))

        except Exception as e:
            conn.rollback()
            flash(f'❌ Error saving trade plan: {str(e)}', 'danger')
            add_log('ERROR', f'Trade plan save error: {e}', 'TradePlan')
        finally:
            conn.close()

    # Get existing trade plans with PROPER field mapping
    conn = get_universal_connection()  # CHANGED: Use universal connection
    try:
        # First, let's check if we need to migrate the database schema
        cursor = conn.cursor()

        # Check if new columns exist, if not, create them - CHANGED: Use universal_execute
        try:
            universal_execute(cursor,
                "SELECT strategy, timeframe, entry_conditions, exit_conditions, risk_percent, reward_percent FROM trade_plans LIMIT 1")
        except Exception:  # CHANGED: Catch general exception for both databases
            # Migrate old schema to new schema
            add_log('INFO', 'Migrating trade_plans schema to new format', 'TradePlan')
            
            # Use universal_execute for all ALTER TABLE statements
            alter_statements = [
                'ALTER TABLE trade_plans ADD COLUMN strategy TEXT',
                'ALTER TABLE trade_plans ADD COLUMN timeframe TEXT',
                'ALTER TABLE trade_plans ADD COLUMN entry_conditions TEXT',
                'ALTER TABLE trade_plans ADD COLUMN exit_conditions TEXT',
                'ALTER TABLE trade_plans ADD COLUMN risk_percent REAL',
                'ALTER TABLE trade_plans ADD COLUMN reward_percent REAL',
                'ALTER TABLE trade_plans ADD COLUMN plan_date DATE'
            ]
            
            for alter_stmt in alter_statements:
                try:
                    universal_execute(cursor, alter_stmt)
                except Exception as alter_error:
                    # Column might already exist, continue
                    add_log('DEBUG', f'Column creation (may already exist): {alter_error}', 'TradePlan')
                    continue

            # Migrate existing data from old fields to new fields - CHANGED: Use universal_execute
            universal_execute(cursor, '''
                UPDATE trade_plans 
                SET strategy = CASE 
                    WHEN trade_plan LIKE '% - %' THEN substr(trade_plan, 1, instr(trade_plan, ' - ') - 1)
                    ELSE trade_plan 
                END,
                timeframe = CASE 
                    WHEN trade_plan LIKE '% - %' THEN substr(trade_plan, instr(trade_plan, ' - ') + 3)
                    ELSE 'N/A'
                END,
                entry_conditions = CASE 
                    WHEN condition LIKE 'Entry:%' THEN substr(condition, 1, instr(condition, 'Exit:') - 1)
                    ELSE condition
                END,
                exit_conditions = CASE 
                    WHEN condition LIKE '%Exit:%' THEN substr(condition, instr(condition, 'Exit:'))
                    ELSE ''
                END,
                risk_percent = CASE 
                    WHEN notes LIKE 'Risk:%' THEN CAST(replace(substr(notes, instr(notes, 'Risk:') + 5, instr(notes, '%,') - instr(notes, 'Risk:') - 5), '%', '') AS REAL)
                    ELSE NULL
                END,
                reward_percent = CASE 
                    WHEN notes LIKE '%Reward:%' THEN CAST(replace(substr(notes, instr(notes, 'Reward:') + 7, instr(notes, '%', instr(notes, 'Reward:')) - instr(notes, 'Reward:') - 7), '%', '') AS REAL)
                    ELSE NULL
                END,
                plan_date = date
            ''')
            conn.commit()

        # Now query with proper field names - CHANGED: Use conn_fetch_dataframe
        plans = conn_fetch_dataframe(conn, '''
            SELECT 
                id,
                plan_date,
                symbol,
                strategy,
                timeframe,
                entry_conditions,
                exit_conditions,
                risk_percent,
                reward_percent,
                status,
                outcome,
                created_at
            FROM trade_plans 
            ORDER BY created_at DESC
        ''')

        plans_dict = plans.to_dict('records') if not plans.empty else []

        # Debug output
        print(f"DEBUG: Loaded {len(plans_dict)} trade plans")
        for plan in plans_dict:
            print(f"  Plan {plan.get('id')}: {plan.get('symbol')} - {plan.get('strategy')}")

    except Exception as e:
        add_log('ERROR', f'Error loading trade plans: {e}', 'TradePlan')
        plans_dict = []
        print(f"ERROR loading trade plans: {e}")
    finally:
        conn.close()

    return render_template('trade_plan.html',
                           form=form,
                           trade_plans=plans_dict,
                           current_date=datetime.now().strftime('%Y-%m-%d'))


# ======== EDIT TRADE PLAN ROUTE ========
@app.route('/edit_trade_plan/<int:plan_id>', methods=['POST'])
@login_required
def edit_trade_plan(plan_id):
    """Edit a trade plan - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()  # CHANGED: Use universal connection
        cursor = conn.cursor()

        # Get form data
        symbol = request.form.get('symbol', '').upper()
        strategy = request.form.get('strategy', '')
        timeframe = request.form.get('timeframe', '')
        plan_date = request.form.get('plan_date', '')
        entry_conditions = request.form.get('entry_conditions', '')
        exit_conditions = request.form.get('exit_conditions', '')
        risk_percent = request.form.get('risk_percent')
        reward_percent = request.form.get('reward_percent')
        status = request.form.get('status', 'pending')
        outcome = request.form.get('outcome', '')

        # Update the trade plan with PROPER field names - CHANGED: Use universal_execute
        universal_execute(cursor, '''
            UPDATE trade_plans SET
                plan_date = ?, 
                symbol = ?, 
                strategy = ?, 
                timeframe = ?,
                entry_conditions = ?,
                exit_conditions = ?,
                risk_percent = ?,
                reward_percent = ?,
                status = ?, 
                outcome = ?
            WHERE id = ?
        ''', (
            plan_date,
            symbol,
            strategy,
            timeframe,
            entry_conditions,
            exit_conditions,
            risk_percent,
            reward_percent,
            status,
            outcome if outcome else None,
            plan_id
        ))

        conn.commit()
        flash('✅ Trade plan updated successfully!', 'success')
        add_log('INFO', f'Trade plan {plan_id} updated', 'TradePlan')

    except Exception as e:
        conn.rollback()
        flash(f'❌ Error updating trade plan: {str(e)}', 'danger')
        add_log('ERROR', f'Trade plan update error: {e}', 'TradePlan')
        print(f"ERROR updating trade plan: {e}")
    finally:
        conn.close()

    return redirect(url_for('trade_plan'))


# ======== DELETE TRADE PLAN ROUTE ========
@app.route('/delete_trade_plan/<int:plan_id>')
@login_required
def delete_trade_plan(plan_id):
    """Delete a trade plan - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()  # CHANGED: Use universal connection
        cursor = conn.cursor()

        universal_execute(cursor, 'DELETE FROM trade_plans WHERE id = ?', (plan_id,))  # CHANGED: Use universal_execute
        conn.commit()

        flash('✅ Trade plan deleted successfully!', 'success')
        add_log('INFO', f'Trade plan {plan_id} deleted', 'TradePlan')

    except Exception as e:
        conn.rollback()
        flash(f'❌ Error deleting trade plan: {str(e)}', 'danger')
        add_log('ERROR', f'Trade plan delete error: {e}', 'TradePlan')
    finally:
        conn.close()

    return redirect(url_for('trade_plan'))


# ======== PROFESSIONAL HYBRID CONFIGURATIONS HYBRID MODEL ========

# Professional configuration page - HYBRID COMPATIBLE
from datetime import datetime
import json


@app.route('/configuration', methods=['GET', 'POST'])
@login_required
@hybrid_compatible  # ADDED: Hybrid compatibility
def configuration():
    """Professional configuration with comprehensive error handling - HYBRID VERSION"""
    
    # Use hybrid environment detection
    environment = detect_environment()
    is_desktop = environment == 'sqlite'
    is_web = environment == 'postgresql'

    # Load saved settings with hybrid-aware path
    try:
        config_path = get_hybrid_config_path()
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config_data = {}
        # Initialize with hybrid defaults
        config_data = initialize_hybrid_config()

    # Ensure all required keys exist with safe defaults
    config_data.setdefault('mt5', {}).setdefault('server', '')
    config_data.setdefault('mt5', {}).setdefault('account', '')
    config_data.setdefault('mt5', {}).setdefault('terminal_path', '')
    config_data.setdefault('environment', environment)  # ADDED: Store environment

    if request.method == 'POST':
        # Check CSRF token first
        if not validate_csrf():
            flash('❌ Security token invalid. Please refresh the page and try again.', 'danger')
            return redirect(url_for('configuration'))

        action = request.form.get('action')

        if action == 'connect_with_password':
            # Handle password connection with hybrid awareness
            password = request.form.get('password')
            server = config_data.get('mt5', {}).get('server', '')
            account = config_data.get('mt5', {}).get('account', '')
            terminal_path = config_data.get('mt5', {}).get('terminal_path', '')

            if not all([password, server, account]):
                flash('❌ Please fill all required fields: Server, Account, and Password', 'danger')
            else:
                try:
                    print(f"🔗 Attempting MT5 connection: {account}@{server}")

                    success = mt5_manager.initialize_connection(
                        int(account),
                        password,
                        server,
                        terminal_path
                    )

                    if success:
                        session['mt5_authenticated'] = True
                        session['mt5_password'] = password
                        
                        # ADDED: Hybrid-aware success message
                        if is_desktop:
                            flash('✅ MT5 connected successfully! (Desktop Mode)', 'success')
                        else:
                            flash('✅ MT5 connected successfully! (Web Mode)', 'success')
                            
                        add_log('INFO', f'MT5 connected to {server} - Account: {account} - Environment: {environment}', 'Configuration')
                    else:
                        error_msg = mt5.last_error() if MT5_AVAILABLE else "MT5 not available"
                        
                        # ADDED: Hybrid-aware error handling
                        if is_web:
                            flash(f'❌ Web mode: Using demo data. MT5 Error: {error_msg}', 'warning')
                        else:
                            flash(f'❌ Connection failed. Error: {error_msg}', 'danger')
                            
                        add_log('ERROR', f'MT5 connection failed: {error_msg} - Environment: {environment}', 'Configuration')

                except Exception as e:
                    # ADDED: Hybrid error handling
                    if is_web:
                        flash('⚠️ Web mode: Using demo data. Connection not required.', 'info')
                    else:
                        flash(f'❌ Connection error: {str(e)}', 'danger')
                    add_log('ERROR', f'MT5 connection exception: {e} - Environment: {environment}', 'Configuration')

        elif action == 'save_settings':
            # Save server settings with hybrid path
            server = request.form.get('server', '').strip()
            account = request.form.get('account', '').strip()
            terminal_path = request.form.get('terminal_path', '').strip()

            if server and account:
                try:
                    account_int = int(account)

                    # UPDATE: Use proper nested structure
                    if 'mt5' not in config_data:
                        config_data['mt5'] = {}
                    
                    config_data['mt5'].update({
                        'server': server,
                        'account': account_int,
                        'terminal_path': terminal_path
                    })
                    
                    # ADDED: Save environment info
                    config_data['environment'] = environment
                    config_data['last_updated'] = datetime.now().isoformat()

                    # UPDATE: Use hybrid config path
                    config_path = get_hybrid_config_path()
                    with open(config_path, 'w') as f:
                        json.dump(config_data, f, indent=4)

                    flash('✅ Server settings saved successfully!', 'success')
                    add_log('INFO', f'MT5 settings saved: {account_int}@{server} - Environment: {environment}', 'Configuration')

                    # Clear connection state when settings change
                    session.pop('mt5_authenticated', None)
                    session.pop('mt5_password', None)

                    return redirect(url_for('configuration'))

                except ValueError:
                    flash('❌ Account number must be numeric', 'danger')
                except Exception as e:
                    flash(f'❌ Error saving settings: {str(e)}', 'danger')
            else:
                flash('⚠️ Please fill all required fields: Server and Account', 'danger')

        elif action == 'disconnect':
            try:
                mt5_manager.shutdown()
                session.pop('mt5_authenticated', None)
                session.pop('mt5_password', None)
                flash('🔌 MT5 disconnected successfully', 'info')
                add_log('INFO', f'MT5 disconnected by user - Environment: {environment}', 'Configuration')
            except Exception as e:
                flash(f'❌ Error disconnecting: {str(e)}', 'danger')

            return redirect(url_for('configuration'))

        elif action == 'switch_mode':  # ADDED: Hybrid mode switching
            # This would handle manual mode switching if needed
            current_mode = "Desktop" if is_desktop else "Web"
            flash(f'ℹ️ Currently in {current_mode} mode. Auto-detection is active.', 'info')
            return redirect(url_for('configuration'))

    # Determine connection status with hybrid awareness
    is_connected = mt5_manager.connected and session.get('mt5_authenticated', False)
    
    # ADDED: Enhanced status for template
    connection_status = {
        'connected': is_connected,
        'environment': environment,
        'is_desktop': is_desktop,
        'is_web': is_web,
        'demo_mode': not is_connected,
        'mt5_available': MT5_AVAILABLE
    }

    return render_template('configuration.html',
                           mt5_connected=is_connected,
                           config=config_data.get('mt5', {}),  # Pass only MT5 config to template
                           authenticated=session.get('mt5_authenticated', False),
                           connection_status=connection_status,  # ADDED: Enhanced status
                           environment=environment)  # ADDED: Environment info


def get_hybrid_config_path():
    """Get appropriate config path based on environment"""
    environment = detect_environment()
    
    if environment == 'postgresql':
        # Web environment - use current directory
        return "config.json"
    else:
        # Desktop environment - use user config directory
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal')
        else:  # Linux/Mac
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'mt5journal')
        
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')


def initialize_hybrid_config():
    """Initialize configuration with hybrid defaults"""
    environment = detect_environment()
    
    return {
        'mt5': {
            'server': '',
            'account': 0,
            'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
            'password': ''  # Note: passwords should not be stored in plain text
        },
        'environment': environment,
        'created_at': datetime.now().isoformat(),
        'hybrid_mode': True
    }


def validate_csrf():
    """Validate CSRF token safely"""
    try:
        from flask_wtf.csrf import validate_csrf
        validate_csrf(request.form.get('csrf_token'))
        return True
    except:
        return False


@app.route('/enter_password', methods=['GET', 'POST'])
@login_required
@hybrid_compatible  # ADDED: Hybrid compatibility
def enter_password():
    """Enter password for MT5 connection - HYBRID VERSION"""

    # Load saved settings with hybrid path
    try:
        config_path = get_hybrid_config_path()
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = initialize_hybrid_config()

    if request.method == 'POST':
        password = request.form.get('password')
        environment = detect_environment()

        if password:
            # Test connection with entered password
            mt5_config = config_data.get('mt5', {})
            if all(k in mt5_config for k in ['account', 'server']):
                success = mt5_manager.initialize_connection(
                    mt5_config['account'],
                    password,
                    mt5_config['server'],
                    mt5_config.get('terminal_path', '')
                )

                if success:
                    # Store password in session (encrypted by Flask)
                    session['mt5_authenticated'] = True
                    session['mt5_password'] = password  # Temporary session storage
                    
                    # ADDED: Environment-specific message
                    if environment == 'sqlite':
                        flash('✅ Password accepted! MT5 connected in Desktop Mode.', 'success')
                    else:
                        flash('✅ Password accepted! MT5 connected in Web Mode.', 'success')
                        
                    return redirect('/configuration')
                else:
                    # ADDED: Hybrid-aware error
                    if environment == 'postgresql':
                        flash('⚠️ Web mode: Using demo data. Live connection not required.', 'info')
                    else:
                        flash('❌ Connection failed. Check password and try again.', 'danger')
            else:
                flash('No MT5 configuration found. Please set up server and account first.', 'danger')

    return render_template('enter_password.html',
                           config=config_data.get('mt5', {}))


# Debug routes - HYBRID COMPATIBLE
@app.route('/debug/mt5_connection')
@login_required
@hybrid_compatible
def debug_mt5_connection():
    """Professional MT5 connection debug - HYBRID VERSION"""
    environment = detect_environment()
    status = mt5_manager.connected
    message = f"MT5 {'Connected' if status else 'Not Connected'} - {environment.upper()} Mode"
    details = {
        'status': status,
        'message': message,
        'connection_attempts': mt5_manager.connection_attempts,
        'last_connection': mt5_manager.last_connection,
        'mt5_available': MT5_AVAILABLE,
        'environment': environment,
        'is_desktop': environment == 'sqlite',
        'is_web': environment == 'postgresql',
        'demo_mode': not status
    }
    return render_template('debug/mt5_connection.html', **details)


@app.route('/debug/data_flow_test')
@login_required
@hybrid_compatible
def debug_data_flow_test():
    """Professional data flow test - HYBRID VERSION"""
    environment = detect_environment()
    return render_template('debug/data_flow_test.html', 
                          environment=environment,
                          is_desktop=environment == 'sqlite')


@app.route('/debug/import_test')
@login_required
@hybrid_compatible
def debug_import_test():
    """Professional import test - HYBRID VERSION"""
    environment = detect_environment()
    return render_template('debug/import_test.html',
                          environment=environment,
                          is_desktop=environment == 'sqlite')


@app.route('/debug/force_correct_connection')
@login_required
@hybrid_compatible
def debug_force_correct_connection():
    """Force professional MT5 reconnection - HYBRID VERSION"""
    environment = detect_environment()
    try:
        # ADDED: Environment-aware reconnection
        if environment == 'postgresql':
            return jsonify({
                'success': True, 
                'message': 'Web mode - using demo data (reconnection not required)',
                'environment': environment
            })
        
        success = mt5_manager.reconnect()
        if success:
            add_log('INFO', f'Force reconnection successful - Environment: {environment}', 'Debug')
            return jsonify({
                'success': True, 
                'message': 'MT5 reconnected successfully',
                'environment': environment
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'MT5 reconnection failed',
                'environment': environment
            })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e),
            'environment': environment
        })


@app.route('/api/test_connection', methods=['POST'])
@login_required
@hybrid_compatible
def test_connection():
    """Test MT5 connection with detailed error reporting - HYBRID VERSION"""
    environment = detect_environment()
    
    # ADDED: Early return for web mode
    if environment == 'postgresql':
        return jsonify({
            'success': True,
            'message': '✅ Web mode - demo data active (live connection not required)',
            'environment': environment,
            'demo_mode': True
        })
    
    try:
        account = request.form.get('account')
        password = request.form.get('password')
        server = request.form.get('server')
        terminal_path = request.form.get('terminal_path', '')

        if not all([account, password, server]):
            return jsonify({
                'success': False,
                'error': 'Please fill all required fields: Account, Password, and Server',
                'environment': environment
            })

        # Validate account is numeric
        try:
            account_int = int(account)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Account number must be numeric',
                'environment': environment
            })

        # Test the connection
        if not MT5_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'MT5 platform not available. Running in demo mode.',
                'environment': environment
            })

        # Initialize connection
        if not mt5.initialize(
            path=terminal_path,
            login=account_int,
            password=password,
            server=server
        ):
            error_code = mt5.last_error()
            error_msg = get_mt5_error_message(error_code)
            return jsonify({
                'success': False,
                'error': f'MT5 Error {error_code}: {error_msg}',
                'environment': environment
            })

        # Verify connection by getting account info
        account_info = mt5.account_info()
        if account_info:
            # Success - shutdown test connection
            mt5.shutdown()
            return jsonify({
                'success': True,
                'message': f'✅ Connected successfully to {server} - Account: {account_info.login}',
                'account_info': {
                    'login': account_info.login,
                    'balance': account_info.balance,
                    'currency': account_info.currency,
                    'server': account_info.server
                },
                'environment': environment
            })
        else:
            mt5.shutdown()
            return jsonify({
                'success': False,
                'error': 'Connected but failed to retrieve account information',
                'environment': environment
            })

    except Exception as e:
        # Ensure MT5 is shutdown on error
        if MT5_AVAILABLE:
            mt5.shutdown()
        return jsonify({
            'success': False,
            'error': f'Connection test failed: {str(e)}',
            'environment': environment
        })


def get_mt5_error_message(error_code):
    """Get human-readable MT5 error messages"""
    error_messages = {
        10013: "Invalid account number",
        10014: "Invalid password", 
        10015: "Invalid server",
        10016: "Invalid terminal path",
        10017: "Trade context is busy",
        10018: "Connection failed",
        10019: "Network error",
        10020: "Timeout error"
    }
    return error_messages.get(error_code, f"MT5 error code: {error_code}")


# ADDED: Hybrid configuration API endpoint
@app.route('/api/hybrid_status')
@login_required
def api_hybrid_status():
    """Get current hybrid configuration status"""
    environment = detect_environment()
    config_path = get_hybrid_config_path()
    
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except:
        config_data = {}
    
    return jsonify({
        'environment': environment,
        'config_path': config_path,
        'config_exists': os.path.exists(config_path),
        'mt5_configured': bool(config_data.get('mt5', {}).get('server')),
        'is_desktop': environment == 'sqlite',
        'is_web': environment == 'postgresql',
        'mt5_connected': mt5_manager.connected,
        'demo_mode': not mt5_manager.connected
    })

# -----------------------------------------------------------------------------
# PROFESSIONAL API ENDPOINTS
# -----------------------------------------------------------------------------
@app.route('/api/stats/<period>')
@login_required
def api_stats(period):
    """Professional API endpoint for trading statistics"""
    try:
        conn = get_db_connection()

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        elif period == '3months':
            start_date = end_date - timedelta(days=90)
        elif period == '6months':
            start_date = end_date - timedelta(days=180)
        elif period == '1year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime(1970, 1, 1)  # All time

        query = '''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ? 
            ORDER BY exit_time DESC
        '''
        df = pd.read_sql(query, conn, params=(start_date,))

        stats = stats_generator.generate_trading_statistics(df, period.capitalize()) if not df.empty else create_empty_stats()
        return jsonify(stats)

    except Exception as e:
        add_log('ERROR', f'Professional API stats error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/equity_curve')
@login_required
def api_equity_curve():
    """Professional equity curve API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('''
            SELECT timestamp, equity, balance 
            FROM account_history 
            ORDER BY timestamp
        ''', conn)

        if df.empty:
            # Generate professional demo equity curve
            base_equity = 10000
            timestamps = []
            equity = []
            balance = []

            for i in range(90):  # 90 days of data
                date = (datetime.now() - timedelta(days=89-i)).strftime('%Y-%m-%d')
                timestamps.append(date)

                # Simulate realistic equity curve with trends
                daily_change = np.random.normal(50, 200)  # Normal distribution
                base_equity += daily_change
                base_equity = max(5000, base_equity)  # Prevent going too low

                equity.append(round(base_equity, 2))
                balance.append(round(base_equity * 0.95, 2))  # Balance slightly below equity

            return jsonify({
                'timestamps': timestamps,
                'equity': equity,
                'balance': balance
            })

        return jsonify({
            'timestamps': df['timestamp'].astype(str).tolist(),
            'equity': df['equity'].tolist(),
            'balance': df['balance'].tolist()
        })

    except Exception as e:
        add_log('ERROR', f'Professional equity curve API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/trade_results_data')
@login_required
def api_trade_results_data():
    """Professional trade results API"""
    period = request.args.get('period', 'monthly')

    try:
        conn = get_db_connection()

        # Date filtering based on period
        end_date = datetime.now()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=365)

        query = '''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ?
            ORDER BY exit_time DESC
        '''
        df = pd.read_sql(query, conn, params=(start_date,))

        trades_data = df.to_dict('records') if not df.empty else []
        return jsonify({'trades': trades_data})

    except Exception as e:
        add_log('ERROR', f'Professional trade results API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/calendar/<int:year>/<int:month>')
@login_required
def api_calendar(year, month):
    """Professional calendar API"""
    try:
        calendar_data = calendar_dashboard.get_monthly_calendar(year, month)
        return jsonify(calendar_data)
    except Exception as e:
        add_log('ERROR', f'Professional calendar API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar_pnl')
@login_required
def api_calendar_pnl():
    """Professional calendar PnL API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('''
            SELECT date, daily_pnl, closed_trades, win_rate, winning_trades, losing_trades
            FROM calendar_pnl 
            ORDER BY date
        ''', conn)

        calendar_data = df.to_dict('records') if not df.empty else []
        return jsonify({'calendar': calendar_data})

    except Exception as e:
        add_log('ERROR', f'Professional calendar PnL API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/logs')
@login_required
def api_logs():
    """Professional logs API"""
    return jsonify({'logs': advanced_logger.log_messages[-100:]})  # Last 100 logs

@app.route('/api/profit_loss_distribution')
@login_required
def api_profit_loss_distribution():
    """Professional P/L distribution API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('SELECT profit FROM trades WHERE status = "CLOSED"', conn)

        if df.empty:
            return jsonify({'winning': 0, 'losing': 0, 'break_even': 0})

        winning = int((df['profit'] > 0).sum())
        losing = int((df['profit'] < 0).sum())
        break_even = int((df['profit'] == 0).sum())

        return jsonify({
            'winning': winning,
            'losing': losing,
            'break_even': break_even
        })

    except Exception as e:
        add_log('ERROR', f'Professional P/L distribution API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# PROFESSIONAL EXPORT ROUTES
# -----------------------------------------------------------------------------
@app.route('/export/csv')
@login_required
def export_csv():
    """Professional CSV export"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('SELECT * FROM trades ORDER BY entry_time DESC', conn)

        if df.empty:
            # Create professional demo CSV data
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Ticket', 'Symbol', 'Type', 'Volume', 'Entry', 'Exit', 'Profit', 'RR Ratio', 'Duration', 'Status'])
            writer.writerow([500001, 'EURUSD', 'BUY', '0.1', '1.0950', '1.0980', '30.0', '2.0', '2h 30m', 'CLOSED'])
            writer.writerow([500002, 'GBPUSD', 'SELL', '0.1', '1.2750', '1.2720', '30.0', '1.5', '1h 15m', 'CLOSED'])
            writer.writerow([500003, 'XAUUSD', 'BUY', '0.01', '1950.50', '1955.25', '47.5', '2.3', '4h 45m', 'CLOSED'])
        else:
            # Export professional data
            output = io.StringIO()
            df.to_csv(output, index=False)

        output.seek(0)
        filename = f"professional_mt5_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        add_log('ERROR', f'Professional CSV export error: {e}', 'Export')
        flash('Error exporting CSV', 'danger')
        return redirect(url_for('professional_dashboard'))

@app.route('/export/pdf')
@login_required
def export_pdf():
    """Professional PDF export"""
    if not reportlab_available:
        flash('PDF export requires ReportLab installation', 'warning')
        return redirect(url_for('professional_dashboard'))

    try:
        # Create professional PDF report
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        # Title
        elements.append(Paragraph("Professional MT5 Trading Journal Report", title_style))
        elements.append(Spacer(1, 12))

        # Date
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 20))

        # Get data for report
        conn = get_db_connection()
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)

        if not df.empty:
            stats = stats_generator.generate_trading_statistics(df)

            # Summary table
            summary_data = [
                ['Metric', 'Value'],
                ['Total Trades', stats.get('total_trades', 0)],
                ['Net Profit', f"${stats.get('net_profit', 0):.2f}"],
                ['Win Rate', f"{stats.get('win_rate', 0):.1f}%"],
                ['Profit Factor', f"{stats.get('profit_factor', 0):.2f}"],
                ['Avg Trade', f"${stats.get('avg_trade', 0):.2f}"],
                ['Largest Win', f"${stats.get('largest_win', 0):.2f}"],
                ['Largest Loss', f"${stats.get('largest_loss', 0):.2f}"]
            ]

            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(summary_table)

        conn.close()

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        filename = f"professional_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        add_log('ERROR', f'Professional PDF export error: {e}', 'Export')
        flash('Error generating PDF report', 'danger')
        return redirect(url_for('professional_dashboard'))


# =============================================================================
# RISK ANALYSIS ROUTES
# =============================================================================

@app.route('/risk_analysis')
@login_required
def risk_analysis():
    @hybrid_compatible 
    """Comprehensive Risk Analysis Dashboard"""
    period = request.args.get('period', 'monthly')

    # AUTO-DETECTION: This will now switch automatically
    is_demo_mode = not get_mt5_connection_status()

    try:
        conn = get_db_connection()
        df = get_trades_by_period(conn, period)

        if df.empty:
            # Return DEMO data structure if no data (NOT empty)
            return render_template('statistics/risk_analysis.html',
                                   risk_metrics=get_demo_risk_metrics(),  # CHANGED FROM {}
                                   risk_recommendations=get_demo_risk_recommendations(),  # CHANGED FROM []
                                   detailed_metrics=get_demo_detailed_risk_metrics(),  # CHANGED FROM []
                                   risk_chart_data=get_demo_risk_chart_data(),  # CHANGED FROM {}
                                   drawdown_chart_data=get_demo_drawdown_chart_data(),  # CHANGED FROM {}
                                   concentration_chart_data=get_demo_concentration_chart_data(),  # CHANGED FROM {}
                                   current_period=period,
                                   is_demo_mode=is_demo_mode,
                                   auto_refresh=True)

        # Calculate comprehensive risk metrics
        risk_metrics = calculate_comprehensive_risk_metrics(df)
        risk_recommendations = generate_risk_recommendations(risk_metrics)
        detailed_metrics = generate_detailed_risk_metrics(df, risk_metrics)

        # Generate chart data
        risk_chart_data = generate_risk_distribution_chart_data(df)
        drawdown_chart_data = generate_drawdown_chart_data(df)
        concentration_chart_data = generate_risk_concentration_data(df)

        return render_template('statistics/risk_analysis.html',
                               risk_metrics=risk_metrics,
                               risk_recommendations=risk_recommendations,
                               detailed_metrics=detailed_metrics,
                               risk_chart_data=risk_chart_data,
                               drawdown_chart_data=drawdown_chart_data,
                               concentration_chart_data=concentration_chart_data,
                               current_period=period,
                               is_demo_mode=is_demo_mode,
                               auto_refresh=True)

    except Exception as e:
        add_log('ERROR', f'Risk analysis error: {e}', 'RiskAnalysis')
        # Fallback to DEMO data on error (NOT empty)
        return render_template('statistics/risk_analysis.html',
                               risk_metrics=get_demo_risk_metrics(),  # CHANGED FROM {}
                               risk_recommendations=get_demo_risk_recommendations(),  # CHANGED FROM []
                               detailed_metrics=get_demo_detailed_risk_metrics(),  # CHANGED FROM []
                               risk_chart_data=get_demo_risk_chart_data(),  # CHANGED FROM {}
                               drawdown_chart_data=get_demo_drawdown_chart_data(),  # CHANGED FROM {}
                               concentration_chart_data=get_demo_concentration_chart_data(),  # CHANGED FROM {}
                               current_period=period,
                               is_demo_mode=True,
                               auto_refresh=True)
    finally:
        conn.close()

def get_demo_risk_metrics():
    """Return demo risk metrics for testing when real data is unavailable"""
    return {
        'overall_score': 65,
        'max_drawdown': 15.5,
        'sharpe_ratio': 1.2,
        'win_rate': 58.3,
        'profit_factor': 1.8,
        'avg_win_loss_ratio': 1.5,
        'risk_reward_ratio': 1.7,
        'volatility': 12.3,
        'concentration_risk': 45.0,
        'consistency_score': 72.0
    }


# =============================================================================
# TREND ANALYSIS ROUTES
# =============================================================================

def get_demo_trend_metrics():
    """Demo data for trend analysis when real data is unavailable"""
    return {
        'equity_trend': 1.5,
        'performance_trend': 2.1,
        'monthly_trend': 0.8,
        'pattern_strength': 75,
        'trend_consistency': 82,
        'momentum_score': 68,
        'volatility_trend': -0.3,
        'market_direction': 1,
        'trend_duration': 15,
        'prediction_confidence': 78,
        'overall_score': 72,
        'consistency_score': 82  # Make sure this line has a comma if you add more lines
    }  # ← THIS CLOSING BRACE MUST BE HERE


@app.route('/trend_analysis')
@login_required
def trend_analysis():
    @hybrid_compatible 
    """Optimized Trend Analysis Dashboard"""
    period = request.args.get('period', 'monthly')
    is_demo_mode = not get_mt5_connection_status()

    conn = None  # Initialize connection
    try:
        conn = get_db_connection()
        df = get_trades_by_period(conn, period)

        if df.empty:
            # QUICK RETURN - Use demo data for empty datasets
            return render_template('statistics/trend_analysis.html',
                                   trend_metrics=get_demo_trend_metrics(),
                                   trend_insights={
                                       'outlook': 'Bullish',
                                       'summary': 'Demo data showing sample trends',
                                       'recommendation': 'Connect MT5 for real analysis'
                                   },
                                   equity_trend_data={
                                       'dates': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05'],
                                       'equity': [10000, 11500, 12500, 11800, 13200],
                                       'trend': [10000, 11200, 12400, 11600, 12800]
                                   },
                                   trend_distribution=[
                                       {'name': 'Uptrend', 'value': 60},
                                       {'name': 'Sideways', 'value': 25},
                                       {'name': 'Downtrend', 'value': 15}
                                   ],
                                   monthly_trend_data={
                                       'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                                       'pnl': [1500, 1000, -700, 1400, 1100],
                                       'colors': ['success', 'success', 'danger', 'success', 'success']
                                   },
                                   pattern_data={
                                       'values': [1, -1, 1, 1, -1, 1, -1, -1, 1, 1],
                                       'sequence': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                                   },
                                   current_period=period,
                                   is_demo_mode=True,
                                   auto_refresh=True)

        # ONLY calculate if we have real data
        trend_metrics = calculate_trend_metrics(df)
        trend_insights = generate_trend_insights(trend_metrics, df)
        equity_trend_data = generate_equity_trend_data(df)
        trend_distribution = calculate_trend_distribution(df)
        monthly_trend_data = generate_monthly_trend_data(df)
        pattern_data = generate_pattern_analysis_data(df)

        return render_template('statistics/trend_analysis.html',
                               trend_metrics=trend_metrics,
                               trend_insights=trend_insights,
                               equity_trend_data=equity_trend_data,
                               trend_distribution=trend_distribution,
                               monthly_trend_data=monthly_trend_data,
                               pattern_data=pattern_data,
                               current_period=period,
                               is_demo_mode=is_demo_mode,
                               auto_refresh=True)


    except Exception as e:

        add_log('ERROR', f'Trend analysis error: {e}', 'TrendAnalysis')

        # Quick fallback to demo data

        return render_template('statistics/trend_analysis.html',

                               trend_metrics=get_demo_trend_metrics(),

                               trend_insights={

                                   'outlook': 'Bullish',

                                   'summary': 'Demo data - system error occurred',

                                   'recommendation': 'Check connection and try again'

                               },

                               equity_trend_data={

                                   'dates': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05'],

                                   'equity': [10000, 11500, 12500, 11800, 13200],

                                   'trend': [10000, 11200, 12400, 11600, 12800]

                               },

                               trend_distribution=[

                                   {'name': 'Uptrend', 'value': 60},

                                   {'name': 'Sideways', 'value': 25},

                                   {'name': 'Downtrend', 'value': 15}

                               ],

                               monthly_trend_data={

                                   'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],

                                   'pnl': [1500, 1000, -700, 1400, 1100],

                                   'colors': ['success', 'success', 'danger', 'success', 'success']

                               },

                               pattern_data={

                                   'values': [1, -1, 1, 1, -1, 1, -1, -1, 1, 1],

                                   'sequence': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

                               },

                               current_period=period,

                               is_demo_mode=True,

                               auto_refresh=True)
    finally:
        # ALWAYS close connection
        if conn:
            conn.close() # ← MAKE SURE THIS IS ALSO INDENTED
# =============================================================================
# MT5 CONNECTION DETECTION FUNCTIONS (ADD THIS NEW SECTION)
# =============================================================================

def get_mt5_connection_status():
    """
    Check if MT5 is actually connected and receiving live data
    Returns: True if live MT5 connected, False for demo mode
    """
    try:
        # Check if MT5 module is available and initialized
        if 'mt5' not in globals():
            # Try to import MT5
            try:
                import MetaTrader5 as mt5
                globals()['mt5'] = mt5
            except ImportError:
                add_log('WARNING', 'MT5 module not available - using Demo Mode', 'MT5_Status')
                return False

        # Initialize MT5 if not already initialized
        if not mt5.initialize():
            add_log('WARNING', 'MT5 initialization failed - using Demo Mode', 'MT5_Status')
            return False

        # Check if we're actually connected to a server
        account_info = mt5.account_info()
        if account_info is None:
            add_log('WARNING', 'No MT5 account info - using Demo Mode', 'MT5_Status')
            return False

        # Check if we're getting real market data (not just demo data)
        try:
            # Try to get real-time market data for a major symbol
            eurusd_info = mt5.symbol_info("EURUSD")
            if eurusd_info is None:
                add_log('WARNING', 'No market data available - using Demo Mode', 'MT5_Status')
                return False

            # Check if we have recent tick data (indicates live connection)
            tick = mt5.symbol_info_tick("EURUSD")
            if tick is None:
                add_log('WARNING', 'No live tick data - using Demo Mode', 'MT5_Status')
                return False

            # Check if the tick data is recent (within last 60 seconds)
            tick_time = datetime.fromtimestamp(tick.time)
            time_diff = datetime.now() - tick_time
            if time_diff.total_seconds() > 60:
                add_log('WARNING', 'Stale market data - using Demo Mode', 'MT5_Status')
                return False

        except Exception as e:
            add_log('WARNING', f'Market data check failed: {e} - using Demo Mode', 'MT5_Status')
            return False

        # If all checks pass, we're in live mode
        add_log('INFO', 'MT5 Live connection confirmed', 'MT5_Status')
        return True

    except Exception as e:
        add_log('ERROR', f'MT5 connection check failed: {e} - using Demo Mode', 'MT5_Status')
        return False


@app.route('/api/connection_status')
def api_connection_status():
    """API endpoint to check current connection status"""
    is_demo = not get_mt5_connection_status()
    return jsonify({
        'is_demo_mode': is_demo,
        'status': 'demo' if is_demo else 'live',
        'timestamp': datetime.now().isoformat(),
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


# =============================================================================
# RISK ANALYSIS CALCULATION FUNCTIONS (YOUR ORIGINAL CODE - UNCHANGED)
# =============================================================================

def calculate_comprehensive_risk_metrics(df):
    """Calculate comprehensive risk metrics from trades data"""
    if df.empty:
        return {
            'overall_score': 0,
            'risk_level': 'Low',
            'max_drawdown': 0,
            'volatility_score': 0,
            'recovery_factor': 0,
            'sharpe_ratio': 0,
            'var_95': 0,
            'expected_shortfall': 0
        }

    try:
        # Calculate basic risk metrics
        profits = df['profit'].tolist()
        equity_curve = np.cumsum(profits)

        # Max Drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak * 100
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

        # Volatility (standard deviation of returns)
        daily_returns = np.diff(equity_curve) / equity_curve[:-1] * 100 if len(equity_curve) > 1 else [0]
        volatility = np.std(daily_returns) if len(daily_returns) > 0 else 0

        # Sharpe Ratio (simplified)
        sharpe_ratio = np.mean(daily_returns) / volatility if volatility > 0 else 0

        # Value at Risk (95%)
        var_95 = np.percentile(profits, 5) if len(profits) > 0 else 0

        # Expected Shortfall
        losses = [p for p in profits if p < var_95]
        expected_shortfall = np.mean(losses) if losses else var_95

        # Recovery Factor
        net_profit = equity_curve[-1] if len(equity_curve) > 0 else 0
        recovery_factor = net_profit / max_drawdown if max_drawdown > 0 else float('inf')

        # Overall Risk Score (0-100)
        volatility_score = min(100, volatility * 2)
        drawdown_score = min(100, max_drawdown * 3)
        var_score = min(100, abs(var_95) * 10)

        overall_score = (volatility_score + drawdown_score + var_score) / 3

        # Risk Level
        if overall_score < 25:
            risk_level = "Low"
        elif overall_score < 50:
            risk_level = "Moderate"
        elif overall_score < 75:
            risk_level = "High"
        else:
            risk_level = "Extreme"

        return {
            'overall_score': round(overall_score, 1),
            'risk_level': risk_level,
            'max_drawdown': round(max_drawdown, 2),
            'volatility_score': round(volatility_score, 1),
            'recovery_factor': round(recovery_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'var_95': round(var_95, 2),
            'expected_shortfall': round(expected_shortfall, 2)
        }

    except Exception as e:
        add_log('ERROR', f'Risk metrics calculation error: {e}', 'RiskAnalysis')
        return {
            'overall_score': 0,
            'risk_level': 'Unknown',
            'max_drawdown': 0,
            'volatility_score': 0,
            'recovery_factor': 0,
            'sharpe_ratio': 0,
            'var_95': 0,
            'expected_shortfall': 0
        }


def generate_risk_recommendations(risk_metrics):
    """Generate risk management recommendations"""
    recommendations = []

    if risk_metrics['overall_score'] > 70:
        recommendations.extend([
            {
                'category': 'Position Sizing',
                'message': 'Reduce position sizes by 50% immediately due to extreme risk exposure',
                'priority': 'high'
            },
            {
                'category': 'Risk Management',
                'message': 'Implement maximum daily loss limit of 2% of account balance',
                'priority': 'high'
            }
        ])
    elif risk_metrics['overall_score'] > 40:
        recommendations.extend([
            {
                'category': 'Risk Control',
                'message': 'Consider reducing position sizes by 25% to manage volatility',
                'priority': 'medium'
            },
            {
                'category': 'Diversification',
                'message': 'Diversify across more symbols to reduce concentration risk',
                'priority': 'medium'
            }
        ])
    else:
        recommendations.append({
            'category': 'Maintenance',
            'message': 'Current risk levels are well-managed. Maintain current risk parameters',
            'priority': 'low'
        })

    # Drawdown specific recommendations
    if risk_metrics['max_drawdown'] > 20:
        recommendations.append({
            'category': 'Drawdown Control',
            'message': f'Current max drawdown of {risk_metrics["max_drawdown"]}% is concerning. Implement stricter stop-losses',
            'priority': 'high'
        })

    # Volatility recommendations
    if risk_metrics['volatility_score'] > 60:
        recommendations.append({
            'category': 'Volatility Management',
            'message': 'High volatility detected. Consider smoothing trading frequency',
            'priority': 'medium'
        })

    return recommendations


def generate_detailed_risk_metrics(df, risk_metrics):
    """Generate detailed risk metrics table data"""
    if df.empty:
        return []

    try:
        profits = df['profit'].tolist()
        volumes = df['volume'].tolist() if 'volume' in df.columns else [0.1] * len(profits)

        # Calculate additional metrics
        avg_trade_risk = np.mean([abs(p) for p in profits]) if profits else 0
        win_rate = len([p for p in profits if p > 0]) / len(profits) * 100 if profits else 0
        profit_factor = sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0])) if any(
            p < 0 for p in profits) else float('inf')

        # Kelly Criterion
        avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
        avg_loss = np.mean([p for p in profits if p < 0]) if any(p < 0 for p in profits) else 0
        kelly = (win_rate / 100 - (1 - win_rate / 100)) / (avg_win / abs(avg_loss)) if avg_loss != 0 else 0

        detailed_metrics = [
            {
                'name': 'Max Drawdown',
                'value': f"{risk_metrics['max_drawdown']}%",
                'benchmark': '< 10%',
                'status': 'Excellent' if risk_metrics['max_drawdown'] < 10 else 'Good' if risk_metrics[
                                                                                              'max_drawdown'] < 20 else 'Poor',
                'description': 'Maximum peak-to-trough decline in equity'
            },
            {
                'name': 'Sharpe Ratio',
                'value': f"{risk_metrics['sharpe_ratio']}",
                'benchmark': '> 1.0',
                'status': 'Excellent' if risk_metrics['sharpe_ratio'] > 1.5 else 'Good' if risk_metrics[
                                                                                               'sharpe_ratio'] > 1.0 else 'Poor',
                'description': 'Risk-adjusted return metric'
            },
            {
                'name': 'VaR (95%)',
                'value': f"${risk_metrics['var_95']:.2f}",
                'benchmark': '> -2% of equity',
                'status': 'Excellent' if risk_metrics['var_95'] > -20 else 'Good' if risk_metrics[
                                                                                         'var_95'] > -50 else 'Poor',
                'description': 'Maximum expected loss at 95% confidence'
            },
            {
                'name': 'Recovery Factor',
                'value': f"{risk_metrics['recovery_factor']:.2f}",
                'benchmark': '> 1.0',
                'status': 'Excellent' if risk_metrics['recovery_factor'] > 2.0 else 'Good' if risk_metrics[
                                                                                                  'recovery_factor'] > 1.0 else 'Poor',
                'description': 'Net profit divided by max drawdown'
            },
            {
                'name': 'Kelly Criterion',
                'value': f"{kelly:.1%}",
                'benchmark': '< 25%',
                'status': 'Excellent' if kelly < 0.1 else 'Good' if kelly < 0.25 else 'Poor',
                'description': 'Optimal position sizing percentage'
            }
        ]

        return detailed_metrics

    except Exception as e:
        add_log('ERROR', f'Detailed risk metrics error: {e}', 'RiskAnalysis')
        return []


def generate_risk_distribution_chart_data(df):
    """Generate risk distribution chart data"""
    if df.empty:
        return {'labels': [], 'risk_values': []}

    try:
        # Sample last 20 trades for the chart
        sample_trades = df.head(20)
        labels = [f"Trade {i + 1}" for i in range(len(sample_trades))]

        # Calculate risk per trade (simplified as % of profit/volume)
        risk_values = []
        for _, trade in sample_trades.iterrows():
            profit = trade.get('profit', 0)
            volume = trade.get('volume', 0.1)
            risk = abs(profit) / (volume * 1000) * 100 if volume > 0 else 0
            risk_values.append(min(risk, 10))  # Cap at 10% for visualization

        return {
            'labels': labels,
            'risk_values': risk_values
        }

    except Exception as e:
        add_log('ERROR', f'Risk distribution chart error: {e}', 'RiskAnalysis')
        return {'labels': [], 'risk_values': []}


def generate_drawdown_chart_data(df):
    """Generate drawdown analysis chart data"""
    if df.empty:
        return {'dates': [], 'drawdowns': []}

    try:
        profits = df['profit'].tolist()
        equity_curve = np.cumsum(profits)

        # Calculate running drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdowns = ((peak - equity_curve) / peak * 100).tolist()

        # Sample points for chart (max 50 points)
        if len(drawdowns) > 50:
            step = len(drawdowns) // 50
            drawdowns = drawdowns[::step]
            dates = [f"Point {i + 1}" for i in range(len(drawdowns))]
        else:
            dates = [f"Trade {i + 1}" for i in range(len(drawdowns))]

        return {
            'dates': dates,
            'drawdowns': [round(d, 2) for d in drawdowns]
        }

    except Exception as e:
        add_log('ERROR', f'Drawdown chart error: {e}', 'RiskAnalysis')
        return {'dates': [], 'drawdowns': []}


def generate_risk_concentration_data(df):
    """Generate risk concentration chart data"""
    if df.empty:
        return {'labels': [], 'values': []}

    try:
        # Simplified risk concentration analysis
        symbol_risk = 40  # Example value - would calculate from actual data
        strategy_risk = 35
        time_risk = 25

        return {
            'labels': ['Symbol Concentration', 'Strategy Risk', 'Time-based Risk'],
            'values': [symbol_risk, strategy_risk, time_risk]
        }

    except Exception as e:
        add_log('ERROR', f'Risk concentration error: {e}', 'RiskAnalysis')
        return {'labels': [], 'values': []}


# =============================================================================
# TREND ANALYSIS CALCULATION FUNCTIONS (YOUR ORIGINAL CODE - UNCHANGED)
# =============================================================================

def calculate_trend_metrics(df):
    """Calculate comprehensive trend metrics"""
    if df.empty:
        return {
            'equity_trend': 0,
            'equity_trend_strength': 'Unknown',
            'consistency_score': 0,
            'current_streak': 0,
            'streak_trend': 'Unknown',
            'momentum_score': 0
        }

    try:
        profits = df['profit'].tolist()
        equity_curve = np.cumsum(profits)

        # Equity trend calculation
        if len(equity_curve) > 1:
            start_equity = equity_curve[0]
            end_equity = equity_curve[-1]
            equity_trend = ((end_equity - start_equity) / abs(start_equity)) * 100 if start_equity != 0 else 0
        else:
            equity_trend = 0

        # Trend strength (using linear regression)
        if len(equity_curve) > 2:
            x = np.arange(len(equity_curve))
            slope, intercept = np.polyfit(x, equity_curve, 1)
            trend_strength = abs(slope) / (np.std(equity_curve) + 1e-10) * 100
        else:
            trend_strength = 0

        # Consistency score (based on profit consistency)
        positive_months = len([p for p in profits if p > 0])
        consistency_score = (positive_months / len(profits)) * 100 if profits else 0

        # Current streak
        current_streak = 0
        if profits:
            current_profit = profits[-1]
            for profit in reversed(profits):
                if (current_profit > 0 and profit > 0) or (current_profit <= 0 and profit <= 0):
                    current_streak += 1 if current_profit > 0 else -1
                else:
                    break

        # Momentum score (recent performance vs historical)
        if len(profits) > 5:
            recent = profits[-5:]
            historical = profits[:-5]
            recent_avg = np.mean(recent) if recent else 0
            historical_avg = np.mean(historical) if historical else 0
            momentum_score = min(100, max(0, (recent_avg - historical_avg) / (abs(historical_avg) + 1e-10) * 50 + 50))
        else:
            momentum_score = 50

        # Trend strength classification
        if trend_strength > 5:
            trend_strength_text = "Strong"
        elif trend_strength > 2:
            trend_strength_text = "Moderate"
        else:
            trend_strength_text = "Weak"

        # Streak trend classification
        if abs(current_streak) > 3:
            streak_trend = "Significant"
        elif abs(current_streak) > 1:
            streak_trend = "Moderate"
        else:
            streak_trend = "Minor"

        return {
            'equity_trend': round(equity_trend, 2),
            'equity_trend_strength': trend_strength_text,
            'consistency_score': round(consistency_score, 1),
            'current_streak': current_streak,
            'streak_trend': streak_trend,
            'momentum_score': round(momentum_score, 1)
        }

    except Exception as e:
        add_log('ERROR', f'Trend metrics calculation error: {e}', 'TrendAnalysis')
        return {
            'equity_trend': 0,
            'equity_trend_strength': 'Unknown',
            'consistency_score': 0,
            'current_streak': 0,
            'streak_trend': 'Unknown',
            'momentum_score': 0
        }


def generate_trend_insights(trend_metrics, df):
    """Generate trend insights and predictions"""
    insights = []

    # Equity trend insights
    if trend_metrics['equity_trend'] > 5:
        insights.append({
            'title': 'Strong Uptrend Detected',
            'description': f"Equity is trending upward with {trend_metrics['equity_trend']}% growth and {trend_metrics['equity_trend_strength'].lower()} momentum.",
            'sentiment': 'positive',
            'recommendation': 'Consider maintaining or slightly increasing position sizes during confirmed uptrends.'
        })
    elif trend_metrics['equity_trend'] < -5:
        insights.append({
            'title': 'Downtrend Identified',
            'description': f"Equity shows a downward trend of {trend_metrics['equity_trend']}% with {trend_metrics['equity_trend_strength'].lower()} momentum.",
            'sentiment': 'negative',
            'recommendation': 'Reduce position sizes and implement stricter risk management during downtrends.'
        })
    else:
        insights.append({
            'title': 'Sideways Market Phase',
            'description': "Equity is moving sideways with no strong directional bias.",
            'sentiment': 'neutral',
            'recommendation': 'Focus on range-bound strategies and careful position sizing.'
        })

    # Consistency insights
    if trend_metrics['consistency_score'] > 70:
        insights.append({
            'title': 'High Performance Consistency',
            'description': f"Your trading shows excellent consistency with a {trend_metrics['consistency_score']}% score.",
            'sentiment': 'positive',
            'recommendation': 'Maintain your current disciplined approach to trading.'
        })

    # Streak insights
    if abs(trend_metrics['current_streak']) > 3:
        streak_type = 'winning' if trend_metrics['current_streak'] > 0 else 'losing'
        insights.append({
            'title': f'Significant {streak_type.capitalize()} Streak',
            'description': f"Currently on a {abs(trend_metrics['current_streak'])}-trade {streak_type} streak.",
            'sentiment': 'positive' if streak_type == 'winning' else 'negative',
            'recommendation': 'Avoid overconfidence during winning streaks and review strategy during losing streaks.'
        })

    # Momentum insights
    if trend_metrics['momentum_score'] > 70:
        insights.append({
            'title': 'Strong Positive Momentum',
            'description': "Recent performance shows strong positive momentum compared to historical averages.",
            'sentiment': 'positive',
            'recommendation': 'Consider capitalizing on positive momentum with careful position sizing.'
        })

    # Overall outlook
    positive_insights = len([i for i in insights if i['sentiment'] == 'positive'])
    negative_insights = len([i for i in insights if i['sentiment'] == 'negative'])

    if positive_insights > negative_insights:
        overall_outlook = "Bullish"
    elif negative_insights > positive_insights:
        overall_outlook = "Bearish"
    else:
        overall_outlook = "Neutral"

    return {
        'insights': insights,
        'overall_outlook': overall_outlook
    }


def generate_equity_trend_data(df):
    """Generate equity trend chart data"""
    if df.empty:
        return {'dates': [], 'equity': [], 'trend_line': []}

    try:
        profits = df['profit'].tolist()
        equity_curve = np.cumsum(profits).tolist()

        # Generate trend line using linear regression
        if len(equity_curve) > 1:
            x = np.arange(len(equity_curve))
            slope, intercept = np.polyfit(x, equity_curve, 1)
            trend_line = (slope * x + intercept).tolist()
        else:
            trend_line = equity_curve

        # Sample data for chart (max 100 points)
        if len(equity_curve) > 100:
            step = len(equity_curve) // 100
            equity_curve = equity_curve[::step]
            trend_line = trend_line[::step]
            dates = [f"Point {i + 1}" for i in range(len(equity_curve))]
        else:
            dates = [f"Trade {i + 1}" for i in range(len(equity_curve))]

        return {
            'dates': dates,
            'equity': [round(e, 2) for e in equity_curve],
            'trend_line': [round(t, 2) for t in trend_line]
        }

    except Exception as e:
        add_log('ERROR', f'Equity trend data error: {e}', 'TrendAnalysis')
        return {'dates': [], 'equity': [], 'trend_line': []}


def calculate_trend_distribution(df):
    """Calculate trend distribution for pie chart"""
    if df.empty:
        return [33, 34, 33]  # Equal distribution for demo

    try:
        profits = df['profit'].tolist()

        # Simple trend classification (this would be more sophisticated in production)
        uptrend_periods = 40  # Example values
        sideways_periods = 35
        downtrend_periods = 25

        return [uptrend_periods, sideways_periods, downtrend_periods]

    except Exception as e:
        add_log('ERROR', f'Trend distribution error: {e}', 'TrendAnalysis')
        return [33, 34, 33]


def generate_monthly_trend_data(df):
    """Generate monthly trend analysis data"""
    if df.empty or 'exit_time' not in df.columns:
        return {'months': [], 'pnl': [], 'colors': []}

    try:
        # Group by month (simplified)
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        monthly_pnl = df.groupby(df['exit_time'].dt.to_period('M'))['profit'].sum()

        months = [str(period) for period in monthly_pnl.index]
        pnl = monthly_pnl.tolist()

        # Colors based on PnL
        colors = []
        for profit in pnl:
            if profit > 0:
                colors.append('rgba(28, 200, 138, 0.8)')  # Green
            elif profit < 0:
                colors.append('rgba(231, 74, 59, 0.8)')  # Red
            else:
                colors.append('rgba(108, 117, 125, 0.8)')  # Gray

        return {
            'months': months[-12:],  # Last 12 months
            'pnl': [round(p, 2) for p in pnl[-12:]],
            'colors': colors[-12:]
        }

    except Exception as e:
        add_log('ERROR', f'Monthly trend data error: {e}', 'TrendAnalysis')
        return {'months': [], 'pnl': [], 'colors': []}


def generate_pattern_analysis_data(df):
    """Generate win/loss pattern analysis data"""
    if df.empty:
        return {'sequence': [], 'values': [], 'point_colors': []}

    try:
        profits = df['profit'].tolist()[-30:]  # Last 30 trades

        # Convert to win/loss sequence (1 for win, -1 for loss, 0 for break-even)
        sequence = []
        values = []
        point_colors = []

        for i, profit in enumerate(profits):
            sequence.append(f"T{i + 1}")
            if profit > 0:
                values.append(1)
                point_colors.append('rgba(28, 200, 138, 1)')  # Green
            elif profit < 0:
                values.append(-1)
                point_colors.append('rgba(231, 74, 59, 1)')  # Red
            else:
                values.append(0)
                point_colors.append('rgba(108, 117, 125, 1)')  # Gray

        return {
            'sequence': sequence,
            'values': values,
            'point_colors': point_colors
        }

    except Exception as e:
        add_log('ERROR', f'Pattern analysis error: {e}', 'TrendAnalysis')
        return {'sequence': [], 'values': [], 'point_colors': []}

# =============================================================================
# QUANTUM PROFESSIONAL JOURNAL AI Q&A ROUTES
# =============================================================================

@app.route('/ai_qa')
@login_required
def ai_qa():
    @hybrid_compatible 
    """Quantum Professional Journal AI Q&A Dashboard"""
    return render_template('ai_qa.html')


@app.route('/api/ai/get_user_stats')
@login_required
def api_ai_user_stats():
    @hybrid_compatible 
    """Get comprehensive user statistics for AI analysis"""
    try:
        conn = get_db_connection()

        # Get trading statistics
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
        stats = stats_generator.generate_trading_statistics(df) if not df.empty else create_empty_stats()

        # Get recent trades for context
        recent_trades = pd.read_sql(
            'SELECT * FROM trades ORDER BY entry_time DESC LIMIT 20', conn
        ).to_dict('records') if not df.empty else []

        # Get account data
        account_data = data_synchronizer.get_account_data()

        # Get psychology logs if available
        psychology_stats = {}
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    AVG(confidence_level) as avg_confidence,
                    AVG(stress_level) as avg_stress,
                    AVG(discipline_level) as avg_discipline
                FROM psychology_logs WHERE user_id = ?
            ''', (current_user.id,))
            psych_result = cursor.fetchone()
            if psych_result:
                psychology_stats = {
                    'avg_confidence': psych_result[0] or 0,
                    'avg_stress': psych_result[1] or 0,
                    'avg_discipline': psych_result[2] or 0
                }
        except:
            pass

        conn.close()

        return jsonify({
            'trading_stats': stats,
            'account_data': account_data,
            'psychology_stats': psychology_stats,
            'recent_trades_sample': recent_trades[:5],  # Send only 5 for context
            'total_trades_count': len(df) if not df.empty else 0
        })

    except Exception as e:
        add_log('ERROR', f'AI user stats error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/trade_analysis/<int:trade_id>')
@login_required
def api_ai_trade_analysis(trade_id):
    @hybrid_compatible 
    """Get specific trade data for AI analysis"""
    try:
        conn = get_db_connection()

        # Get the specific trade
        trade_df = pd.read_sql(
            'SELECT * FROM trades WHERE id = ? OR ticket_id = ?',
            conn, params=(trade_id, trade_id)
        )

        if trade_df.empty:
            return jsonify({'error': 'Trade not found'}), 404

        trade_data = trade_df.iloc[0].to_dict()

        # Get similar trades for context
        symbol = trade_data.get('symbol', '')
        similar_trades = pd.read_sql('''
            SELECT * FROM trades 
            WHERE symbol = ? AND status = "CLOSED" 
            ORDER BY entry_time DESC LIMIT 10
        ''', conn, params=(symbol,)).to_dict('records')

        conn.close()

        return jsonify({
            'trade': trade_data,
            'similar_trades': similar_trades,
            'analysis_context': {
                'symbol': symbol,
                'trade_type': trade_data.get('type'),
                'profitability': trade_data.get('profit', 0) > 0
            }
        })

    except Exception as e:
        add_log('ERROR', f'AI trade analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/coach_advice', methods=['POST'])
@login_required
def api_ai_coach_advice():
    """Get AI trading coach advice based on user data"""
    try:
        data = request.get_json()
        timeframe = data.get('timeframe', 'weekly')

        # Get comprehensive user data
        conn = get_db_connection()

        # Calculate date range based on timeframe
        end_date = datetime.now()
        if timeframe == 'daily':
            start_date = end_date - timedelta(days=1)
        elif timeframe == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif timeframe == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)  # default weekly

        # Get trades for the period
        trades_df = pd.read_sql('''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ?
            ORDER BY exit_time DESC
        ''', conn, params=(start_date,))

        stats = stats_generator.generate_trading_statistics(trades_df,
                                                            timeframe) if not trades_df.empty else create_empty_stats()

        # Get current market context (simplified)
        market_context = {
            'current_time': datetime.now().isoformat(),
            'timeframe': timeframe,
            'analysis_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        }

        conn.close()

        # Generate AI coach advice (in real implementation, this would call an AI service)
        advice = generate_ai_coach_advice(stats, market_context, timeframe)

        return jsonify({
            'advice': advice,
            'timeframe': timeframe,
            'stats_snapshot': {
                'win_rate': stats.get('win_rate', 0),
                'profit_factor': stats.get('profit_factor', 0),
                'total_trades': stats.get('total_trades', 0),
                'net_profit': stats.get('net_profit', 0)
            },
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI coach advice error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/risk_assessment')
@login_required
def api_ai_risk_assessment():
    """Get AI-powered risk assessment"""
    try:
        conn = get_db_connection()

        # Get recent trades for risk analysis
        recent_trades = pd.read_sql('''
            SELECT * FROM trades 
            WHERE entry_time >= DATE('now', '-30 days')
            ORDER BY entry_time DESC
        ''', conn)

        # Get account history for drawdown analysis
        account_history = pd.read_sql('''
            SELECT equity, balance, timestamp 
            FROM account_history 
            WHERE timestamp >= DATE('now', '-30 days')
            ORDER BY timestamp
        ''', conn)

        conn.close()

        # Calculate risk metrics
        risk_metrics = calculate_risk_metrics(recent_trades, account_history)
        risk_assessment = generate_risk_assessment(risk_metrics)

        return jsonify({
            'risk_level': risk_assessment['level'],
            'risk_score': risk_assessment['score'],
            'recommendations': risk_assessment['recommendations'],
            'metrics': risk_metrics,
            'assessment_date': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI risk assessment error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/market_analysis', methods=['POST'])
@login_required
def api_ai_market_analysis():
    """Get AI-powered market analysis"""
    try:
        data = request.get_json()
        analysis_type = data.get('type', 'intraday')

        # Get user's trading preferences and history
        conn = get_db_connection()

        # Get most traded symbols
        symbol_stats = pd.read_sql('''
            SELECT symbol, COUNT(*) as trade_count, AVG(profit) as avg_profit
            FROM trades 
            WHERE status = "CLOSED"
            GROUP BY symbol 
            ORDER BY trade_count DESC 
            LIMIT 5
        ''', conn)

        # Get user's best performing timeframes
        performance_by_hour = pd.read_sql('''
            SELECT strftime('%H', entry_time) as hour, 
                   AVG(profit) as avg_profit,
                   COUNT(*) as trade_count
            FROM trades 
            WHERE status = "CLOSED"
            GROUP BY hour
            ORDER BY avg_profit DESC
        ''', conn)

        conn.close()

        # Generate market analysis based on user's trading style
        market_analysis = generate_market_analysis(
            symbol_stats.to_dict('records'),
            performance_by_hour.to_dict('records'),
            analysis_type
        )

        return jsonify({
            'analysis': market_analysis,
            'user_preferences': {
                'top_symbols': symbol_stats.to_dict('records'),
                'best_hours': performance_by_hour.to_dict('records')
            },
            'analysis_type': analysis_type,
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI market analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/psychology_analysis', methods=['POST'])
@login_required
def api_ai_psychology_analysis():
    """AI-powered trading psychology analysis"""
    try:
        data = request.get_json()
        mood_data = data.get('mood_data', {})

        # Get psychology logs if available
        conn = get_db_connection()

        psychology_logs = []
        try:
            psychology_logs = pd.read_sql('''
                SELECT * FROM psychology_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            ''', conn, params=(current_user.id,)).to_dict('records')
        except:
            pass

        # Get trading performance correlated with psychology
        performance_data = pd.read_sql('''
            SELECT date(exit_time) as trade_date, 
                   SUM(profit) as daily_pnl,
                   COUNT(*) as trade_count
            FROM trades 
            WHERE status = "CLOSED" AND exit_time >= DATE('now', '-30 days')
            GROUP BY trade_date
            ORDER BY trade_date
        ''', conn)

        conn.close()

        # Generate psychology analysis
        psychology_analysis = generate_psychology_analysis(
            mood_data,
            psychology_logs,
            performance_data.to_dict('records')
        )

        return jsonify({
            'analysis': psychology_analysis,
            'mood_data': mood_data,
            'has_psychology_history': len(psychology_logs) > 0
        })

    except Exception as e:
        add_log('ERROR', f'AI psychology analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/custom_question', methods=['POST'])
@login_required
def api_ai_custom_question():
    """Handle custom AI questions with trading context"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        category = data.get('category', 'general')

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # Get comprehensive user context
        conn = get_db_connection()

        # Get relevant data based on question category
        context_data = get_question_context(conn, category, question)

        conn.close()

        # Generate AI response
        ai_response = generate_ai_response(question, category, context_data)

        # Store the Q&A interaction (optional)
        store_ai_interaction(question, ai_response, category)

        return jsonify({
            'question': question,
            'answer': ai_response,
            'category': category,
            'context_used': context_data.get('context_type', 'general'),
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI custom question error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500


# =============================================================================
# AI ANALYSIS GENERATION FUNCTIONS
# =============================================================================

def generate_ai_coach_advice(stats, market_context, timeframe):
    """Generate AI trading coach advice based on statistics"""

    win_rate = stats.get('win_rate', 0)
    profit_factor = stats.get('profit_factor', 0)
    total_trades = stats.get('total_trades', 0)
    net_profit = stats.get('net_profit', 0)
    avg_rr = stats.get('avg_rr', 0)

    advice = []

    # Performance-based advice
    if win_rate < 40:
        advice.append(
            "Your win rate is below 40%. Focus on improving entry timing and trade selection. Consider waiting for higher probability setups.")
    elif win_rate > 60:
        advice.append(
            "Excellent win rate above 60%! Your trade selection is strong. Consider scaling up position sizes gradually while maintaining risk management.")
    else:
        advice.append("Solid win rate. Focus on consistency and risk management to improve profitability.")

    # Risk-Reward advice
    if avg_rr < 1.0:
        advice.append(
            "Your risk-reward ratio is below 1.0. Work on letting winners run and cutting losses quickly. Aim for at least 1.5:1 R:R ratio.")
    elif avg_rr > 2.0:
        advice.append(
            "Outstanding risk-reward management! Your ability to let profits run while controlling losses is excellent.")

    # Profit factor advice
    if profit_factor < 1.0:
        advice.append(
            "Profit factor below 1.0 indicates overall unprofitability. Review your strategy and risk management approach.")
    elif profit_factor > 2.0:
        advice.append("Exceptional profit factor! Your trading edge is well-defined and effectively executed.")

    # Volume advice
    if total_trades < 10:
        advice.append(
            "Low trade volume detected. Consider whether you're being too selective or missing opportunities. Review your trading plan.")
    elif total_trades > 50 and timeframe == 'weekly':
        advice.append(
            "High trade frequency. Ensure you're not overtrading. Quality over quantity often leads to better results.")

    return " ".join(advice)


def calculate_risk_metrics(trades_df, account_history):
    """Calculate comprehensive risk metrics"""
    if trades_df.empty:
        return {
            'drawdown': 0,
            'volatility': 0,
            'risk_score': 0,
            'position_concentration': 0,
            'recent_loss_streak': 0
        }

    # Calculate max drawdown from account history
    drawdown = 0
    if not account_history.empty:
        equity_curve = account_history['equity'].tolist()
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            current_dd = (peak - equity) / peak * 100
            if current_dd > drawdown:
                drawdown = current_dd

    # Calculate other risk metrics
    recent_profits = trades_df['profit'].tolist() if not trades_df.empty else []
    volatility = np.std(recent_profits) if recent_profits else 0

    # Calculate loss streak
    loss_streak = 0
    current_streak = 0
    for profit in recent_profits:
        if profit < 0:
            current_streak += 1
            loss_streak = max(loss_streak, current_streak)
        else:
            current_streak = 0

    # Position concentration
    if not trades_df.empty:
        symbol_counts = trades_df['symbol'].value_counts()
        concentration = symbol_counts.iloc[0] / len(trades_df) * 100 if len(trades_df) > 0 else 0
    else:
        concentration = 0

    # Overall risk score (0-100, higher = more risk)
    risk_score = min(100, drawdown * 2 + volatility / 10 + concentration / 2 + loss_streak * 10)

    return {
        'drawdown': round(drawdown, 2),
        'volatility': round(volatility, 2),
        'risk_score': round(risk_score, 2),
        'position_concentration': round(concentration, 2),
        'recent_loss_streak': loss_streak
    }


def generate_risk_assessment(risk_metrics):
    """Generate risk assessment based on metrics"""
    risk_score = risk_metrics['risk_score']
    drawdown = risk_metrics['drawdown']

    if risk_score < 25:
        level = "LOW"
        recommendations = [
            "Your risk exposure is well-controlled",
            "Consider gradual position size increases for quality setups",
            "Maintain current risk management practices"
        ]
    elif risk_score < 50:
        level = "MODERATE"
        recommendations = [
            "Monitor position sizes and correlation",
            "Ensure stop-losses are properly placed",
            "Consider reducing trade frequency if drawdown increases"
        ]
    elif risk_score < 75:
        level = "HIGH"
        recommendations = [
            "Reduce position sizes by 25-50% immediately",
            "Implement stricter daily loss limits",
            "Focus only on highest probability setups",
            "Review recent losing trades for patterns"
        ]
    else:
        level = "EXTREME"
        recommendations = [
            "REDUCE POSITION SIZES BY 50-75% IMMEDIATELY",
            "Implement maximum daily loss limit of 2%",
            "Trade only 1-2 highest conviction setups per day",
            "Consider taking a break to review strategy"
        ]

    return {
        'level': level,
        'score': risk_score,
        'recommendations': recommendations
    }


def generate_market_analysis(top_symbols, best_hours, analysis_type):
    """Generate market analysis based on user's trading style"""

    analysis = f"Market Analysis for {analysis_type.upper()} Trading:\n\n"

    # Symbol-specific analysis
    if top_symbols:
        analysis += "Based on your trading history, your most active symbols are:\n"
        for symbol in top_symbols[:3]:
            analysis += f"- {symbol['symbol']}: {symbol['trade_count']} trades, Avg PnL: ${symbol['avg_profit']:.2f}\n"
        analysis += "\n"

    # Time-based analysis
    if best_hours:
        best_hour = best_hours[0] if best_hours else {}
        analysis += f"Your most profitable trading hour: {best_hour.get('hour', 'N/A')}:00\n"
        analysis += f"Average profit during this hour: ${best_hour.get('avg_profit', 0):.2f}\n\n"

    # Strategy recommendations based on analysis type
    if analysis_type == 'intraday':
        analysis += "Intraday Strategy Focus:\n"
        analysis += "- Monitor key support/resistance levels\n"
        analysis += "- Use shorter timeframes for entry timing\n"
        analysis += "- Implement tight stop-losses\n"
        analysis += "- Take partial profits at technical levels\n"
    elif analysis_type == 'swing':
        analysis += "Swing Trading Strategy Focus:\n"
        analysis += "- Focus on daily chart patterns\n"
        analysis += "- Use wider stops for volatility\n"
        analysis += "- Position size for 2-5 day holds\n"
        analysis += "- Monitor macroeconomic developments\n"
    else:
        analysis += "Position Trading Strategy Focus:\n"
        analysis += "- Analyze weekly/monthly charts\n"
        analysis += "- Fundamental analysis is key\n"
        analysis += "- Use position sizing for longer holds\n"
        analysis += "- Monitor trend changes carefully\n"

    return analysis


def generate_psychology_analysis(mood_data, psychology_logs, performance_data):
    """Generate trading psychology analysis"""

    emotion = mood_data.get('emotion', 'neutral')
    confidence = mood_data.get('confidence_level', 3)
    stress = mood_data.get('stress_level', 3)

    analysis = "Trading Psychology Analysis:\n\n"

    # Emotion-based analysis
    if emotion in ['anxious', 'frustrated', 'stressed']:
        analysis += "⚠️  Emotional State Alert:\n"
        analysis += "Your current emotional state may impact trading decisions.\n"
        analysis += "- Consider reducing position sizes temporarily\n"
        analysis += "- Focus on deep breathing before entering trades\n"
        analysis += "- Review your trading plan for confidence\n"
    elif emotion in ['confident', 'calm', 'focused']:
        analysis += "✅  Optimal Mental State:\n"
        analysis += "You're in a good mental state for trading.\n"
        analysis += "- Maintain current emotional discipline\n"
        analysis += "- Stick to your proven strategies\n"
        analysis += "- Avoid overconfidence in winning streaks\n"

    analysis += "\n"

    # Confidence and stress analysis
    if confidence < 3:
        analysis += "Confidence Building Tips:\n"
        analysis += "- Review your successful trades\n"
        analysis += "- Paper trade to rebuild confidence\n"
        analysis += "- Focus on process over outcomes\n"

    if stress > 4:
        analysis += "Stress Management:\n"
        analysis += "- Implement strict risk management\n"
        analysis += "- Take regular breaks during sessions\n"
        analysis += "- Consider meditation or exercise\n"

    # Historical psychology patterns
    if psychology_logs:
        analysis += f"\nBased on {len(psychology_logs)} psychology entries, "
        analysis += "maintain consistent emotional tracking for better self-awareness."

    return analysis


def get_question_context(conn, category, question):
    """Get relevant context data based on question category"""

    context = {'context_type': 'general'}

    try:
        if category == 'performance':
            # Get performance statistics
            df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
            if not df.empty:
                stats = stats_generator.generate_trading_statistics(df)
                context.update({
                    'context_type': 'performance',
                    'win_rate': stats.get('win_rate', 0),
                    'profit_factor': stats.get('profit_factor', 0),
                    'total_trades': stats.get('total_trades', 0),
                    'recent_performance': stats.get('net_profit', 0)
                })

        elif category == 'risk':
            # Get risk-related data
            risk_data = pd.read_sql('''
                SELECT sl_price, profit, volume, symbol 
                FROM trades 
                WHERE status = "CLOSED" 
                ORDER BY entry_time DESC 
                LIMIT 50
            ''', conn)
            context.update({
                'context_type': 'risk',
                'recent_trades_count': len(risk_data),
                'avg_position_size': risk_data['volume'].mean() if not risk_data.empty else 0
            })

        elif category == 'psychology':
            # Get psychology data if available
            try:
                psych_data = pd.read_sql('''
                    SELECT emotion_label, confidence_level, stress_level
                    FROM psychology_logs 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', conn, params=(current_user.id,))
                context.update({
                    'context_type': 'psychology',
                    'recent_moods': psych_data.to_dict('records') if not psych_data.empty else []
                })
            except:
                pass

    except Exception as e:
        add_log('ERROR', f'Question context error: {e}', 'AI_Q&A')

    return context


def generate_ai_response(question, category, context_data):
    """Generate AI response based on question and context"""

    # This is a simplified version - in production, you'd integrate with an AI service
    # like OpenAI GPT, Anthropic Claude, or a local LLM

    responses = {
        'performance': [
            "Based on your trading performance, I recommend focusing on consistency in your approach.",
            "Your performance data shows areas for improvement in risk management and trade timing.",
            "Excellent performance detected! Consider scaling your successful strategies."
        ],
        'risk': [
            "Your risk management appears adequate, but there's room for improvement in position sizing.",
            "Consider implementing stricter stop-loss rules based on recent volatility.",
            "Risk exposure is well-managed. Maintain current risk parameters."
        ],
        'strategy': [
            "Your trading strategy shows promise. Consider backtesting additional market conditions.",
            "Strategy optimization could improve your edge. Review entry and exit criteria.",
            "Solid strategic approach. Focus on execution consistency."
        ],
        'psychology': [
            "Trading psychology is crucial. Consider maintaining an emotion journal.",
            "Your mindset appears balanced. Continue focusing on disciplined execution.",
            "Emotional control can be improved through mindfulness practices."
        ],
        'general': [
            "Based on your trading data, I recommend reviewing your journal regularly for patterns.",
            "Continuous learning and adaptation are key to long-term trading success.",
            "Consider diversifying your strategies across different market conditions."
        ]
    }

    # Select response based on category and context
    category_responses = responses.get(category, responses['general'])

    # Simple context-aware response selection
    if context_data.get('context_type') == 'performance':
        win_rate = context_data.get('win_rate', 0)
        if win_rate > 60:
            response = category_responses[2] if len(category_responses) > 2 else category_responses[0]
        elif win_rate < 40:
            response = category_responses[1] if len(category_responses) > 1 else category_responses[0]
        else:
            response = category_responses[0]
    else:
        response = category_responses[0]

    return f"🤖 Quantum AI Analysis:\n\n{response}\n\nContext: {context_data.get('context_type', 'general analysis')}"


def store_ai_interaction(question, answer, category):
    """Store AI interactions for learning (optional)"""
    # In a production system, you'd store these in a database
    # for improving AI responses over time
    add_log('INFO', f'AI Q&A: {category} - Q: {question[:100]}...', 'AI_Q&A')
    
# Add these routes after your existing dashboard routes
@app.route('/quantum_ai_qa')
def quantum_ai_qa():
    return render_template('ai_qa.html')

@app.route('/performance_metrics')
def performance_metrics():
    return render_template('statistics/executive_dashboard.html')

@app.route('/debug/routes')
def debug_routes():
    """Debug endpoint to see all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': rule.rule
        })
    return jsonify(routes)

# =============================================================================
# LICENSE MANAGEMENT ROUTES
# =============================================================================

@app.route('/license', methods=['GET', 'POST'])
@login_required
def license_management():
    """License management page"""
    license_info = license_manager.get_license_info()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'activate_license':
            license_key = request.form.get('license_key', '').strip().upper()
            if license_key:
                success, message = license_manager.activate_license(license_key)
                if success:
                    flash(f'✅ {message}', 'success')
                else:
                    flash(f'❌ {message}', 'danger')
            else:
                flash('❌ Please enter a license key', 'danger')
                
        elif action == 'extend_trial':
            # For demo purposes - in production this would require payment
            flash('ℹ️ Trial extension requires license purchase', 'info')
    
    return render_template('license.html', 
                         license_info=license_info,
                         current_year=datetime.now().year)

@app.route('/api/license/status')
@login_required
def api_license_status():
    """API endpoint for license status"""
    return jsonify(license_manager.get_license_info())

@app.route('/api/license/activate', methods=['POST'])
@login_required
def api_activate_license():
    """API endpoint for license activation"""
    data = request.get_json()
    license_key = data.get('license_key', '').strip().upper()
    
    if license_key:
        success, message = license_manager.activate_license(license_key)
        return jsonify({'success': success, 'message': message})
    else:
        return jsonify({'success': False, 'message': 'No license key provided'})

@app.route('/api/license/validate')
def api_validate_license():
    """API endpoint for license validation (public)"""
    is_valid, message = license_manager.validate_license()
    return jsonify({
        'valid': is_valid,
        'message': message,
        'trial_days_left': license_manager.get_trial_days_left()
    })

# -----------------------------------------------------------------------------
# PROFESSIONAL SOCKETIO EVENT HANDLERS
# -----------------------------------------------------------------------------
@socketio.on('connect', namespace='/realtime')
def on_professional_connect():
    """Professional client connection handler"""
    add_log('INFO', f'Professional client connected: {request.sid}', 'WebSocket')
    emit('connection_status', {
        'status': 'connected',
        'message': 'Connected to Professional MT5 Journal',
        'timestamp': datetime.now().isoformat()
    })

    # Send professional data snapshot
    with global_data.data_lock:
        emit('data_update', {
            'timestamp': datetime.now().isoformat(),
            'stats': global_data.calculated_stats,
            'account_data': global_data.account_data,
            'open_positions_count': len(global_data.open_positions),
            'last_sync': global_data.last_update.isoformat() if global_data.last_update else None
        })

@socketio.on('disconnect', namespace='/realtime')
def on_professional_disconnect():
    """Professional client disconnection handler"""
    add_log('INFO', f'Professional client disconnected: {request.sid}', 'WebSocket')

@socketio.on('subscribe', namespace='/realtime')
def on_professional_subscribe(data):
    """Professional client subscription handler"""
    channels = data.get('channels', [])
    add_log('INFO', f'Professional client {request.sid} subscribed to: {channels}', 'WebSocket')
    emit('subscribed', {'channels': channels, 'timestamp': datetime.now().isoformat()})

@socketio.on('force_sync', namespace='/realtime')
def on_professional_force_sync():
    """Professional manual sync handler"""
    add_log('INFO', f'Professional manual sync requested by: {request.sid}', 'WebSocket')
    success = data_synchronizer.sync_with_mt5(force=True)
    emit('sync_complete', {
        'success': success,
        'timestamp': datetime.now().isoformat(),
        'message': 'Professional sync completed' if success else 'Sync failed'
    })

@socketio.on('request_calendar', namespace='/realtime')
def on_professional_calendar_request(data):
    """Professional calendar data request handler"""
    try:
        year = data.get('year', datetime.now().year)
        month = data.get('month', datetime.now().month)
        calendar_data = calendar_dashboard.get_monthly_calendar(year, month)
        emit('calendar_data', calendar_data)
    except Exception as e:
        add_log('ERROR', f'Calendar request error: {e}', 'WebSocket')
        emit('calendar_error', {'error': str(e)})

# -----------------------------------------------------------------------------
# PROFESSIONAL APPLICATION INITIALIZATION
# -----------------------------------------------------------------------------
def initialize_application():
    """Professional application initialization with environment awareness"""
    if should_reset_database():
        print("🔄 Development/Reset mode: Initializing trade plans table")
        reset_trade_plans_table()  # <- universal function
    else:
        print("✅ Production mode: Using existing database schema")

# -----------------------------------------------------------------------------
# PROFESSIONAL SHUTDOWN HANDLER
# -----------------------------------------------------------------------------
def professional_shutdown_handler():
    """Professional cleanup on application shutdown"""
    add_log('INFO', 'Professional application shutting down...', 'System')
    auto_sync_thread.stop()
    mt5_manager.shutdown()
    add_log('INFO', 'Professional application shutdown complete', 'System')

# Register shutdown handler
import atexit
atexit.register(professional_shutdown_handler)

# -----------------------------------------------------------------------------
# PROFESSIONAL MAIN EXECUTION
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 PROFESSIONAL MT5 TRADING JOURNAL v2.0")
    print("==============================================")
    print(f"📊 Access URL: http://{config['web_app'].get('host', '127.0.0.1')}:{config['web_app'].get('port', 5000)}")
    print(f"🔐 Authentication: Any username/password (auto-created)")
    print(f"📈 MT5 Status: {'✅ Connected' if mt5_manager.connected else '🔄 Demo Mode'}")
    print(f"🔄 Auto-sync: Every {config['sync'].get('auto_sync_interval', 300)} seconds")
    print(f"📅 Calendar Dashboard: Daily PnL tracking enabled")
    print(f"🎯 Features: Advanced analytics, Universal MT5 configuration")
    print("==============================================")

    # Create professional directory structure
    directories = [
        'templates/trade_results',
        'templates/debug',
        'static/css',
        'static/js',
        'static/images',
        'database/backups',
        'logs',
        'exports'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    try:
        # PROFESSIONAL DATABASE INITIALIZATION - ADD THIS LINE
        initialize_application()

        # Initial professional sync
        threading.Thread(target=data_synchronizer.sync_with_mt5, daemon=True).start()

        # Start professional application
        host = config['web_app'].get('host', '127.0.0.1')
        port = config['web_app'].get('port', 5005)
        debug = config['web_app'].get('debug', False)

        print(f"🌟 Starting professional server on {host}:{port}...")

        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )

    except KeyboardInterrupt:
        print("\n🔴 Professional application interrupted by user")
        professional_shutdown_handler()
    except Exception as e:
        print(f"❌ Professional application error: {e}")
        professional_shutdown_handler()
