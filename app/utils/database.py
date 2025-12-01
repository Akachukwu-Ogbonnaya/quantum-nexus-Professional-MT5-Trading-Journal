# app/utils/database.py
import os
import sqlite3
from .system_info import detect_environment
from datetime import date, datetime

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

class HybridDatabaseManager:
    """Handle database migration between SQLite and PostgreSQL"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def export_to_sqlite(self, postgres_conn, sqlite_path):
        """Export from PostgreSQL to SQLite"""
        try:
            import pandas as pd
            tables = ['trades', 'users', 'account_history', 'calendar_pnl', 'trade_plans', 'market_analysis']
            
            for table in tables:
                # Read from PostgreSQL
                df = pd.read_sql(f'SELECT * FROM {table}', postgres_conn)
                
                # Write to SQLite
                with sqlite3.connect(sqlite_path) as sqlite_conn:
                    df.to_sql(table, sqlite_conn, if_exists='replace', index=False)
            
            return True
        except Exception as e:
            print(f'Export to SQLite failed: {e}')
            return False

class HybridErrorHandler:
    """Handle errors differently for web vs desktop"""
    
    @staticmethod
    def handle_database_error(error, context="Database operation"):
        """Handle database errors appropriately for environment"""
        environment = detect_environment()
        
        if environment == 'postgresql':
            # For web: Log and return JSON error
            return {'success': False, 'error': 'Database operation failed'}
        else:
            # For desktop: Attempt recovery or use demo data
            return {'success': True, 'demo_mode': True, 'message': 'Using demo data'}

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
        import pandas as pd
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
    """Get SQLite connection for local/desktop environment."""
    try:
        # Define DB_PATH for SQLite
        DB_PATH = os.path.join(os.getcwd(), "database", "quantum_journal.db")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        # Connect to SQLite database
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row

        # Enable foreign keys + WAL mode
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        # IMPORTANT: Set database type on the class, NOT on the SQLite connection
        self.db_type = "sqlite"

        return conn

    except Exception as e:
        print(f"❌ SQLite connection failed: {e}")
        raise


def execute_query(self, query, params=None):
    """Execute SQL query with automatic parameter style handling."""
    conn = self.get_connection()
    try:
        cursor = conn.cursor()

        # Convert SQLite-style '?' params → PostgreSQL-style '%s' params
        if self.db_type == "postgresql":
            query = query.replace("?", "%s")

        # Execute query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # SELECT → return rows
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        # Non-select → commit changes
        conn.commit()
        return cursor.rowcount

    except Exception as e:
        conn.rollback()
        print(f"❌ Query failed: {e}")
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
DB_PATH = os.path.join(os.getcwd(), "database", "quantum_journal.db")
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
