# -*- coding: utf-8 -*-

# =============================================================================

# PROFESSIONAL MT5 TRADING JOURNAL - COMPLETE MAIN APPLICATION

# =============================================================================



import os

import json

import threading

import time

import queue

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

    try:

        import psycopg

        from psycopg.rows import dict_row



        def cursor_with_dict(conn):

            return conn.cursor(row_factory=dict_row)



        print(" PostgreSQL mode activated")

    except ImportError:

        USE_POSTGRES = False

        print(" PostgreSQL not available, falling back to SQLite")



if not USE_POSTGRES:

    import sqlite3



    def cursor_with_dict(conn):

        return conn.cursor()



    print(" SQLite mode activated")



# -----------------------------------------------------------------------------

# FLASK IMPORTS

# -----------------------------------------------------------------------------

from flask import (

    Flask,

    render_template,

    request,

    redirect,

    url_for,

    session,

    jsonify,

    send_file,

    abort,

    flash,

    Response,

)

from flask_session import Session

from flask_wtf import CSRFProtect

from flask_login import (

    LoginManager,

    login_user,

    login_required,

    logout_user,

    current_user,

    UserMixin,

)

from werkzeug.security import generate_password_hash, check_password_hash



# SocketIO import with fallback

try:

    from flask_socketio import SocketIO, emit

    SOCKETIO_AVAILABLE = True

except ImportError:

    SOCKETIO_AVAILABLE = False

    print(" Flask-SocketIO not available - real-time features disabled")



# -----------------------------------------------------------------------------

# MT5 AVAILABILITY CHECK

# -----------------------------------------------------------------------------

try:

    import MetaTrader5 as mt5

    MT5_AVAILABLE = True

except ImportError:

    mt5 = None

    MT5_AVAILABLE = False

    print(" MetaTrader5 not installed - running in demo mode")



# -----------------------------------------------------------------------------

# CONFIGURATION MANAGEMENT

# -----------------------------------------------------------------------------

class ConfigManager:

    def __init__(self, config_path="config.json"):

        self.config_path = config_path

        self.config = self.load_or_create_config()



    def load_or_create_config(self):

        if os.path.exists(self.config_path):

            try:

                with open(self.config_path, "r", encoding="utf-8") as f:

                    return json.load(f)

            except Exception as e:

                print(f" Error loading config: {e}")

                return self.create_default_config()

        else:

            return self.create_default_config()



    def create_default_config(self):

        default_config = {

            "mt5": {

                "terminal_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",

                "account": 0,

                "password": "",

                "server": "",

            },

            "web_app": {

                "secret_key": "mt5-journal-pro-" + os.urandom(24).hex(),

                "host": "127.0.0.1",

                "port": 5000,

                "debug": False,

            },

            "database": {"path": "database/trades.db", "backup_interval_hours": 24},

            "sync": {

                "auto_sync_interval": 300,

                "days_history": 90,

                "real_time_updates": True,

            },

            "ui": {"theme": "dark", "charts_enabled": True, "notifications": True},

        }



        try:

            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:

                json.dump(default_config, f, indent=4)

            print(f" Created universal config at {self.config_path}")

        except Exception as e:

            print(f" Error creating config: {e}")



        return default_config



    def update_mt5_config(self, account, password, server, terminal_path=None):

        try:

            self.config["mt5"]["account"] = account

            self.config["mt5"]["password"] = password

            self.config["mt5"]["server"] = server

            if terminal_path:

                self.config["mt5"]["terminal_path"] = terminal_path



            with open(self.config_path, "w", encoding="utf-8") as f:

                json.dump(self.config, f, indent=4)

            print(f" Updated MT5 config for account: {account}")

            return True

        except Exception as e:

            print(f" Error updating MT5 config: {e}")

            return False



# Initialize config

config_manager = ConfigManager()

config = config_manager.config



# -----------------------------------------------------------------------------

# APPLICATION SETUP

# -----------------------------------------------------------------------------

app = Flask(

    __name__,

    static_folder="static",

    template_folder="templates",

    static_url_path="/static",

)



app.secret_key = config["web_app"].get("secret_key", "mt5-journal-pro-secret-2024")

app.config["SESSION_TYPE"] = "filesystem"

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

app.config["SESSION_COOKIE_SECURE"] = False

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"



# Initialize extensions

Session(app)

csrf = CSRFProtect(app)



# Login manager

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please log in to access this page."

login_manager.login_message_category = "info"



# SocketIO with availability check

if SOCKETIO_AVAILABLE:

    socketio = SocketIO(

        app,

        cors_allowed_origins="*",

        ping_interval=25,

        ping_timeout=60,

        async_mode="threading",

    )

else:

    socketio = None

    print(" Real-time features disabled due to missing SocketIO")



# -----------------------------------------------------------------------------

# DATABASE MANAGEMENT

# -----------------------------------------------------------------------------

class HybridDatabaseManager:

    def __init__(self):

        self.db_type = self.detect_environment()



    def detect_environment(self):

        web_indicators = [

            "DATABASE_URL" in os.environ,

            "RAILWAY_ENVIRONMENT" in os.environ,

            "HEROKU" in os.environ,

            "RENDER" in os.environ,

            any("pythonanywhere" in key.lower() for key in os.environ.keys()),

        ]

        return "postgresql" if any(web_indicators) else "sqlite"



    def get_connection(self):

        if self.db_type == "postgresql" and USE_POSTGRES:

            return self.get_postgresql_connection()

        else:

            return self.get_sqlite_connection()



    def get_postgresql_connection(self):

        try:

            database_url = os.environ.get("DATABASE_URL")

            if database_url and database_url.startswith("postgres://"):

                database_url = database_url.replace("postgres://", "postgresql://", 1)



            if database_url:

                conn = psycopg.connect(database_url, row_factory=dict_row)

                conn.db_type = "postgresql"

                return conn

            else:

                conn = psycopg.connect(

                    host=os.environ.get("PGHOST", "localhost"),

                    dbname=os.environ.get("PGDATABASE", "mt5_journal"),

                    user=os.environ.get("PGUSER", "postgres"),

                    password=os.environ.get("PGPASSWORD", ""),

                    port=os.environ.get("PGPORT", 5432),

                    row_factory=dict_row,

                )

                conn.db_type = "postgresql"

                return conn

        except Exception as e:

            print(f" PostgreSQL connection failed: {e}, falling back to SQLite")

            return self.get_sqlite_connection()



    def get_sqlite_connection(self):

        try:

            DB_PATH = config["database"].get("path", "database/trades.db")

            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)



            conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

            conn.row_factory = sqlite3.Row

            conn.db_type = "sqlite"



            conn.execute("PRAGMA foreign_keys = ON")

            conn.execute("PRAGMA journal_mode = WAL")



            return conn

        except Exception as e:

            print(f" SQLite connection failed: {e}")

            raise



# Initialize database manager

db_manager = HybridDatabaseManager()



def get_db_connection():

    return db_manager.get_connection()



# -----------------------------------------------------------------------------

# GLOBAL DATA STORE

# -----------------------------------------------------------------------------

class ProfessionalDataStore:

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



# -----------------------------------------------------------------------------

# PROFESSIONAL CALCULATORS

# -----------------------------------------------------------------------------

class ProfessionalTradingCalculator:

    @staticmethod

    def safe_float_conversion(value, default=0.0):

        """Safely convert any value to float"""

        if value is None:

            return default

        try:

            if isinstance(value, (int, float)):

                return float(value)

            if isinstance(value, str):

                cleaned = (

                    value.replace(",", "").replace("$", "").replace(" ", "").strip()

                )

                if cleaned:

                    return float(cleaned)

            return default

        except (ValueError, TypeError, InvalidOperation):

            return default



    @staticmethod

    def calculate_risk_reward(entry_price, exit_price, sl_price, trade_type):

        """Advanced risk-reward calculation with validation"""

        entry = ProfessionalTradingCalculator.safe_float_conversion(entry_price)

        exit = ProfessionalTradingCalculator.safe_float_conversion(exit_price)

        sl = ProfessionalTradingCalculator.safe_float_conversion(sl_price)



        if sl == 0 or entry == 0 or entry == sl:

            return None



        try:

            trade_type = str(trade_type).upper().strip()



            if trade_type in ["BUY", "BUY_LIMIT", "BUY_STOP"]:

                risk = entry - sl

                reward = exit - entry

            elif trade_type in ["SELL", "SELL_LIMIT", "SELL_STOP"]:

                risk = sl - entry

                reward = entry - exit

            else:

                return None



            if risk != 0:

                rr_ratio = reward / risk

                return round(rr_ratio, 3)



        except Exception as e:

            print(f"Risk-reward calculation error: {e}")

            return None



    @staticmethod

    def calculate_position_size(

        account_balance, risk_percent, entry_price, stop_loss, symbol=None

    ):

        """Professional position sizing with symbol consideration"""

        try:

            account_balance = ProfessionalTradingCalculator.safe_float_conversion(

                account_balance

            )

            risk_amount = account_balance * (

                ProfessionalTradingCalculator.safe_float_conversion(risk_percent) / 100

            )

            price_diff = abs(

                ProfessionalTradingCalculator.safe_float_conversion(entry_price)

                - ProfessionalTradingCalculator.safe_float_conversion(stop_loss)

            )



            if price_diff > 0:

                position_size = risk_amount / price_diff

                max_position = account_balance * 0.1

                position_size = min(position_size, max_position)

                return round(position_size, 4)

        except Exception as e:

            print(f"Position size calculation error: {e}")

        return 0



    @staticmethod

    def calculate_trade_duration(entry_time, exit_time):

        """Calculate trade duration with professional formatting"""

        try:

            if isinstance(entry_time, str):

                try:

                    entry_time = datetime.fromisoformat(

                        entry_time.replace("Z", "+00:00")

                    )

                except Exception:

                    entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")

            if isinstance(exit_time, str):

                try:

                    exit_time = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))

                except Exception:

                    exit_time = datetime.strptime(exit_time, "%Y-%m-%d %H:%M:%S")



            if not exit_time:

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

            print(f"Duration calculation error: {e}")

            return "N/A"



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

            print(f"Max drawdown calculation error: {e}")

            return 0



class ProfessionalStatisticsGenerator:

    @staticmethod

    def generate_trading_statistics(df, period="All Time"):

        """Generate complete trading statistics with period analysis"""

        if df.empty:

            return create_empty_stats()



        try:

            total_trades = len(df)

            winning_trades = len(df[df["profit"] > 0])

            losing_trades = len(df[df["profit"] < 0])

            break_even_trades = len(df[df["profit"] == 0])



            net_profit = float(df["profit"].sum())

            gross_profit = float(df[df["profit"] > 0]["profit"].sum())

            gross_loss = abs(float(df[df["profit"] < 0]["profit"].sum()))



            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            profit_factor = (

                (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

            )



            avg_win = (

                float(df[df["profit"] > 0]["profit"].mean())

                if winning_trades > 0

                else 0

            )

            avg_loss = (

                float(df[df["profit"] < 0]["profit"].mean()) if losing_trades > 0 else 0

            )

            avg_trade = float(df["profit"].mean()) if total_trades > 0 else 0



            return {

                "period": period,

                "total_trades": int(total_trades),

                "winning_trades": int(winning_trades),

                "losing_trades": int(losing_trades),

                "break_even_trades": int(break_even_trades),

                "net_profit": round(net_profit, 2),

                "gross_profit": round(gross_profit, 2),

                "gross_loss": round(gross_loss, 2),

                "win_rate": round(win_rate, 2),

                "profit_factor": round(profit_factor, 2),

                "avg_win": round(avg_win, 2),

                "avg_loss": round(avg_loss, 2),

                "avg_trade": round(avg_trade, 2),

                "max_drawdown": (

                    ProfessionalTradingCalculator.calculate_max_drawdown(

                        df["profit"].cumsum().tolist()

                    )

                    if len(df) > 0

                    else 0.0

                ),

            }



        except Exception as e:

            print(f"Statistics generation error: {e}")

            return create_empty_stats()



# Initialize calculators

trading_calc = ProfessionalTradingCalculator()

stats_generator = ProfessionalStatisticsGenerator()



# -----------------------------------------------------------------------------

# CRITICAL UTILITY FUNCTIONS

# -----------------------------------------------------------------------------

def convert_trade_dates(trades_list):

    """Convert string dates to datetime objects for template compatibility"""

    for trade in trades_list:

        if isinstance(trade.get("entry_time"), str):

            try:

                trade["entry_time"] = datetime.fromisoformat(

                    trade["entry_time"].replace("Z", "+00:00")

                )

            except Exception:

                try:

                    trade["entry_time"] = datetime.strptime(

                        trade["entry_time"], "%Y-%m-%d %H:%M:%S"

                    )

                except Exception:

                    pass

        if isinstance(trade.get("exit_time"), str):

            try:

                trade["exit_time"] = datetime.fromisoformat(

                    trade["exit_time"].replace("Z", "+00:00")

                )

            except Exception:

                try:

                    trade["exit_time"] = datetime.strptime(

                        trade["exit_time"], "%Y-%m-%d %H:%M:%S"

                    )

                except Exception:

                    pass

    return trades_list



def create_empty_stats():

    """Create empty statistics with all required fields for template"""

    return {

        "max_drawdown": 0.0,

        "win_rate": 0.0,

        "profit_factor": 0.0,

        "total_trades": 0,

        "gross_profit": 0.0,

        "gross_loss": 0.0,

        "sharpe_ratio": 0.0,

        "avg_win": 0.0,

        "avg_loss": 0.0,

        "largest_win": 0.0,

        "largest_loss": 0.0,

        "current_drawdown": 0.0,

        "expectancy": 0.0,

        "risk_reward_ratio": 0.0,

        "net_profit": 0.0,

        "winning_trades": 0,

        "losing_trades": 0,

        "avg_trade": 0.0,

        "profit_loss_ratio": 0.0,

        "starting_balance": 0.0,

        "period": "All Time",

    }



def get_trades_by_period(conn, period):

    """Get trades filtered by time period"""

    end_date = datetime.now()



    if period == "daily":

        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    elif period == "weekly":

        start_date = end_date - timedelta(days=end_date.weekday())

    elif period == "monthly":

        start_date = end_date.replace(day=1)

    elif period == "3months":

        start_date = end_date - timedelta(days=90)

    elif period == "6months":

        start_date = end_date - timedelta(days=180)

    elif period == "1year":

        start_date = end_date - timedelta(days=365)

    else:

        # Use dataframe fetch for "All time"

        try:

            import pandas as pd

            return pd.read_sql_query("SELECT * FROM trades", conn)

        except ImportError:

            # Fallback if pandas not available

            cursor = conn.cursor()

            cursor.execute("SELECT * FROM trades")

            trades = cursor.fetchall()

            return trades



    try:

        import pandas as pd

        query = "SELECT * FROM trades WHERE entry_time >= ?"

        return pd.read_sql_query(query, conn, params=(start_date,))

    except ImportError:

        # Fallback if pandas not available

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trades WHERE entry_time >= ?", (start_date,))

        trades = cursor.fetchall()

        return trades



# -----------------------------------------------------------------------------

# BASIC USER MODEL (Fallback if modular import fails)

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

        conn = get_db_connection()

        try:

            cursor = conn.cursor()



            if conn.db_type == "postgresql":

                cursor.execute(

                    "SELECT id, username, password_hash, email, preferences FROM users WHERE id = %s",

                    (user_id,),

                )

            else:

                cursor.execute(

                    "SELECT id, username, password_hash, email, preferences FROM users WHERE id = ?",

                    (user_id,),

                )



            row = cursor.fetchone()

            if row:

                if conn.db_type == "postgresql":

                    user_data = dict(row)

                else:

                    user_data = dict(zip([col[0] for col in cursor.description], row))



                prefs = user_data.get("preferences", "{}")

                if prefs and prefs != "{}":

                    try:

                        preferences = json.loads(prefs)

                    except Exception:

                        preferences = {}

                else:

                    preferences = {}



                return User(

                    user_data["id"],

                    user_data["username"],

                    user_data["password_hash"],

                    user_data.get("email"),

                    preferences,

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

        conn = get_db_connection()

        try:

            cursor = conn.cursor()



            if conn.db_type == "postgresql":

                cursor.execute(

                    "SELECT id, username, password_hash, email, preferences FROM users WHERE username = %s",

                    (username,),

                )

            else:

                cursor.execute(

                    "SELECT id, username, password_hash, email, preferences FROM users WHERE username = ?",

                    (username,),

                )



            row = cursor.fetchone()

            if row:

                if conn.db_type == "postgresql":

                    user_data = dict(row)

                else:

                    user_data = dict(zip([col[0] for col in cursor.description], row))



                prefs = user_data.get("preferences", "{}")

                if prefs and prefs != "{}":

                    try:

                        preferences = json.loads(prefs)

                    except Exception:

                        preferences = {}

                else:

                    preferences = {}



                return User(

                    user_data["id"],

                    user_data["username"],

                    user_data["password_hash"],

                    user_data.get("email"),

                    preferences,

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

        preferences = json.dumps({"theme": "dark", "notifications": True})



        conn = get_db_connection()

        try:

            cursor = conn.cursor()



            if conn.db_type == "postgresql":

                cursor.execute(

                    "INSERT INTO users (username, password_hash, email, preferences) VALUES (%s, %s, %s, %s) RETURNING id",

                    (username, password_hash, email, preferences),

                )

                user_id = cursor.fetchone()[0]

            else:

                cursor.execute(

                    "INSERT INTO users (username, password_hash, email, preferences) VALUES (?, ?, ?, ?)",

                    (username, password_hash, email, preferences),

                )

                user_id = cursor.lastrowid



            conn.commit()

            return User(

                user_id, username, password_hash, email, json.loads(preferences)

            )



        except Exception as e:

            conn.rollback()

            error_msg = str(e).lower()

            if "unique" in error_msg or "duplicate" in error_msg:

                print(f"Username already exists: {username}")

                return None

            else:

                print(f"Database error in User.create: {e}")

                return None

        finally:

            conn.close()



# -----------------------------------------------------------------------------

# USER LOADER

# -----------------------------------------------------------------------------

@login_manager.user_loader

def load_user(user_id):

    try:

        # Try to import from modular structure first

        from app.models.user import User as ModularUser

        return ModularUser.get(int(user_id))

    except ImportError:

        # Fallback to built-in User class

        return User.get(int(user_id))

    except Exception as e:

        print(f"Error loading user: {e}")

        return None



# -----------------------------------------------------------------------------

# BASIC ROUTES (Fallback if blueprints fail)

# -----------------------------------------------------------------------------

@app.route("/")

def index():

    """Professional home page"""

    if current_user.is_authenticated:

        return redirect(url_for("professional_dashboard"))

    return redirect(url_for("login"))



@app.route("/login", methods=["GET", "POST"])

def login():

    """Professional login page"""

    if current_user.is_authenticated:

        return redirect(url_for("professional_dashboard"))



    if request.method == "POST":

        username = request.form.get("username")

        password = request.form.get("password")



        user = User.get_by_username(username)

        if user is None:

            # Auto-create user for demo

            user = User.create(username, password)

            if user:

                print(f"Auto-created professional user: {username}")

                flash("Account created successfully!", "success")



        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            print(f"Professional user logged in: {username}")



            flash(f"Welcome back, {username}!", "success")

            return redirect(url_for("professional_dashboard"))

        else:

            flash("Invalid username or password", "danger")



    return render_template("login.html")



@app.route("/dashboard")

@login_required

def professional_dashboard():

    """Enhanced professional dashboard"""

    try:

        conn = get_db_connection()



        # Get comprehensive statistics

        try:

            import pandas as pd

            df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)

            stats = (

                stats_generator.generate_trading_statistics(df)

                if not df.empty

                else create_empty_stats()

            )

        except ImportError:

            # Fallback without pandas

            stats = create_empty_stats()



        # Get account data

        account_data = {

            "balance": 10000.0,

            "equity": 11500.0,

            "margin": 1250.0,

            "free_margin": 10250.0,

            "currency": "USD",

            "server": "Demo-Server",

        }



        # Get recent trades

        recent_trades = []

        open_positions = []



        conn.close()



        return render_template(

            "dashboard.html",

            stats=stats,

            account_data=account_data,

            recent_trades=recent_trades,

            open_positions=open_positions,

            current_year=datetime.now().year,

            current_month=datetime.now().month,

        )



    except Exception as e:

        print(f"Dashboard error: {e}")

        stats, account_data, recent_trades, open_positions = (

            create_empty_stats(),

            {},

            [],

            [],

        )

        return render_template(

            "dashboard.html",

            stats=stats,

            account_data=account_data,

            recent_trades=recent_trades,

            open_positions=open_positions,

        )



@app.route("/logout")

@login_required

def logout():

    """Professional logout"""

    username = current_user.username

    logout_user()

    print(f"User logged out: {username}")

    flash("You have been logged out successfully.", "info")

    return redirect(url_for("login"))



# -----------------------------------------------------------------------------

# CONTEXT PROCESSOR

# -----------------------------------------------------------------------------

@app.context_processor

def inject_hybrid_data():

    """Inject hybrid-specific data into all templates"""

    environment = db_manager.detect_environment()

    is_demo_mode = not MT5_AVAILABLE



    # Get license information

    try:

        from app.services.license_service import license_manager

        license_info = license_manager.get_license_info()

    except Exception:

        license_info = {

            "status": "free",

            "is_valid": True,

            "trial_days_left": None,

            "features": [

                "full_trading_journal",

                "advanced_analytics",

                "ai_coaching",

                "risk_analysis",

            ],

            "message": "Free Version - All Features Included",

        }



    return {

        "current_time": datetime.now().strftime("%H:%M:%S"),

        "current_date": datetime.now().strftime("%Y-%m-%d"),

        "app_name": "Professional MT5 Journal",

        "app_version": "2.0.0",

        "mt5_connected": MT5_AVAILABLE,

        "demo_mode": is_demo_mode,

        "environment": environment,

        "is_web": environment == "postgresql",

        "is_desktop": environment == "sqlite",

        "db_type": environment,

        "license_status": license_info["status"],

        "license_valid": license_info["is_valid"],

        "trial_days_left": license_info["trial_days_left"],

        "license_features": license_info["features"],

        "license_message": license_info["message"],

    }



# -----------------------------------------------------------------------------

# SOCKETIO EVENT HANDLERS (Conditional)

# -----------------------------------------------------------------------------

if SOCKETIO_AVAILABLE:



    @socketio.on("connect", namespace="/realtime")

    def on_professional_connect():

        """Professional client connection handler"""

        print(f"Professional client connected: {request.sid}")

        emit(

            "connection_status",

            {

                "status": "connected",

                "message": "Connected to Professional MT5 Journal",

                "timestamp": datetime.now().isoformat(),

            },

        )



        # Send professional data snapshot

        with global_data.data_lock:

            emit(

                "data_update",

                {

                    "timestamp": datetime.now().isoformat(),

                    "stats": global_data.calculated_stats,

                    "account_data": global_data.account_data,

                    "open_positions_count": len(global_data.open_positions),

                    "last_sync": (

                        global_data.last_update.isoformat()

                        if global_data.last_update

                        else None

                    ),

                },

            )



    @socketio.on("disconnect", namespace="/realtime")

    def on_professional_disconnect():

        """Professional client disconnection handler"""

        print(f"Professional client disconnected: {request.sid}")



    @socketio.on("subscribe", namespace="/realtime")

    def on_professional_subscribe(data):

        """Professional client subscription handler"""

        channels = data.get("channels", [])

        print(f"Professional client {request.sid} subscribed to: {channels}")

        emit(

            "subscribed",

            {"channels": channels, "timestamp": datetime.now().isoformat()},

        )



# -----------------------------------------------------------------------------

# BLUEPRINT REGISTRATION (Conditional)

# -----------------------------------------------------------------------------

def register_blueprints():

    """Register all blueprints with fallback handling"""

    try:

        from app.routes.auth import auth_bp

        app.register_blueprint(auth_bp)

        print(" Auth blueprint registered")

    except Exception as e:

        print(f" Auth blueprint not available: {e}")



    try:

        from app.routes.dashboard import dashboard_bp

        app.register_blueprint(dashboard_bp)

        print(" Dashboard blueprint registered")

    except Exception as e:

        print(f" Dashboard blueprint not available: {e}")



    try:

        from app.routes.analytics import analytics_bp

        app.register_blueprint(analytics_bp)

        print(" Analytics blueprint registered")

    except Exception as e:

        print(f" Analytics blueprint not available: {e}")



    try:

        from app.routes.api import api_bp

        app.register_blueprint(api_bp, url_prefix="/api")

        print(" API blueprint registered")

    except Exception as e:

        print(f" API blueprint not available: {e}")



# -----------------------------------------------------------------------------

# LICENSE MIDDLEWARE

# -----------------------------------------------------------------------------

@app.before_request

def check_license():

    """Check license status before each request"""

    # Skip license check for certain routes

    exempt_routes = ["static", "login", "register", "logout"]



    if request.endpoint in exempt_routes:

        return



    # Check license status

    try:

        from app.services.license_service import license_manager

        is_valid, message = license_manager.validate_license()



        if not is_valid:

            if request.endpoint not in ["license_management"]:

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":

                    return (

                        jsonify(

                            {

                                "error": "License required",

                                "message": message,

                            }

                        ),

                        402,

                    )

                else:

                    flash(f" {message}. Please activate your license.", "warning")

    except Exception as e:

        # If license service fails, allow access but log error

        print(f"License check failed: {e}")



# -----------------------------------------------------------------------------

# APPLICATION INITIALIZATION

# -----------------------------------------------------------------------------

def initialize_application():

    """Initialize all application services"""

    print(" Initializing Professional MT5 Trading Journal...")



    try:

        # Initialize database

        from app.utils.database import init_database

        init_database()

        print(" Database initialized successfully")

    except Exception as e:

        print(f" Database initialization warning: {e}")



    try:

        # Initialize MT5 manager

        from app.services.mt5_service import mt5_manager

        environment = db_manager.detect_environment()



        if environment == "sqlite" and MT5_AVAILABLE:

            print(" Attempting MT5 connection for desktop mode...")

            mt5_manager.initialize_connection()

        else:

            print(" Web mode or MT5 unavailable - using demo data")

            mt5_manager.initialize_demo_mode()

    except Exception as e:

        print(f" MT5 service initialization warning: {e}")



    try:

        # Register blueprints

        register_blueprints()

        print(" Blueprints registered successfully")

    except Exception as e:

        print(f" Blueprint registration warning: {e}")



    print(" Application initialization complete")



# Initialize on first request

@app.before_first_request

def before_first_request():

    initialize_application()



# -----------------------------------------------------------------------------

# ERROR HANDLERS

# -----------------------------------------------------------------------------

@app.errorhandler(404)

def not_found_error(error):

    return render_template("errors/404.html"), 404



@app.errorhandler(500)

def internal_error(error):

    return render_template("errors/500.html"), 500



# -----------------------------------------------------------------------------

# APPLICATION ENTRY POINT

# -----------------------------------------------------------------------------

if __name__ == "__main__":

    print(" PROFESSIONAL MT5 TRADING JOURNAL v2.0")

    print("==============================================")

    print(

        f" Access URL: http://{config['web_app'].get('host', '127.0.0.1')}:{config['web_app'].get('port', 5000)}"

    )

    print(f" Authentication: Any username/password (auto-created)")

    print(f" MT5 Status: {' Available' if MT5_AVAILABLE else ' Demo Mode'}")

    print(

        f" Auto-sync: Every {config['sync'].get('auto_sync_interval', 300)} seconds"

    )

    print("==============================================")



    try:

        # Create professional directory structure

        directories = [

            "templates/trade_results",

            "templates/debug",

            "templates/errors",

            "static/css",

            "static/js",

            "static/images",

            "database/backups",

            "logs",

            "exports",

        ]



        for directory in directories:

            os.makedirs(directory, exist_ok=True)



        # Start professional application

        host =  "0.0.0.0"

        port = int(os.environ.get("PORT", 8080))

        debug = config["web_app"].get("debug", False)



        print(f" Starting professional server on {host}:{port}...")



        if SOCKETIO_AVAILABLE:

            socketio.run(

                app,

                host=host,

                port=port,

                debug=debug,

                use_reloader=False,

                allow_unsafe_werkzeug=True,

            )

        else:

            app.run(host=host, port=port, debug=debug, use_reloader=False)



    except KeyboardInterrupt:

        print("\n Professional application interrupted by user")

    except Exception as e:


        print(f" Professional application error: {e}")

