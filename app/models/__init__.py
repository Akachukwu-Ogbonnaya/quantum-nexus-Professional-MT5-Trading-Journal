# app/models/__init__.py
from flask import current_app
from flask_login import UserMixin
import functools

# Import all models
from .user import User
from .trade import Trade
from .analytics import Analytics
from .license import LicenseManager, License

# Export all models for easy access
__all__ = [
    'User',
    'Trade', 
    'Analytics',
    'LicenseManager',
    'License'
]

# Database connection management
def with_db_connection(func):
    """Decorator to provide database connection to model methods"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get database connection from app context
        db_manager = current_app.db_manager
        conn = db_manager.get_connection()
        try:
            # Inject connection as first argument if needed
            if 'conn' in func.__code__.co_varnames:
                return func(conn, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        finally:
            conn.close()
    return wrapper

def get_db_connection():
    """Get database connection from current app context"""
    return current_app.db_manager.get_connection()

# Model initialization functions
def init_models(app):
    """Initialize all models with the application context"""
    
    # Set up model relationships and ensure database schema
    with app.app_context():
        try:
            # Import database utilities
            from app.utils.database import init_database
            
            # Initialize database schema
            init_database()
            
            # Verify all models can connect to database
            test_model_connections()
            
            app.logger.add_log('INFO', 'Models initialization completed successfully', 'Models')
            
        except Exception as e:
            app.logger.add_log('ERROR', f'Models initialization failed: {e}', 'Models')
            raise

def test_model_connections():
    """Test that all models can connect to database properly"""
    try:
        # Test User model connection
        users_count = User.get_all_count()
        current_app.logger.add_log('DEBUG', f'User model connection test: {users_count} users', 'Models')
        
        # Test Trade model connection  
        trades_count = Trade.get_all_count()
        current_app.logger.add_log('DEBUG', f'Trade model connection test: {trades_count} trades', 'Models')
        
        # Test License model
        license_manager = LicenseManager()
        license_info = license_manager.get_license_info()
        current_app.logger.add_log('DEBUG', f'License model test: {license_info["status"]}', 'Models')
        
    except Exception as e:
        current_app.logger.add_log('ERROR', f'Model connection test failed: {e}', 'Models')
        # Don't raise - allow application to start in demo mode

# Model utility functions
class ModelUtils:
    """Utility functions shared across models"""
    
    @staticmethod
    def safe_float_conversion(value, default=0.0):
        """Safely convert any value to float"""
        if value is None:
            return default
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = value.replace(',', '').replace('$', '').replace(' ', '').strip()
                if cleaned:
                    return float(cleaned)
            return default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def convert_trade_dates(trades_list):
        """Convert string dates to datetime objects for template compatibility"""
        from datetime import datetime
        
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
    
    @staticmethod
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

# Add utility methods to base models
def enhance_models():
    """Add utility methods to model classes"""
    
    # Add count method to User model
    @classmethod
    def user_get_all_count(cls):
        """Get total user count"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                cursor.execute('SELECT COUNT(*) FROM users')
            else:
                cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    User.get_all_count = user_get_all_count
    
    # Add count method to Trade model
    @classmethod
    def trade_get_all_count(cls):
        """Get total trade count"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                cursor.execute('SELECT COUNT(*) FROM trades')
            else:
                cursor.execute('SELECT COUNT(*) FROM trades')
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    Trade.get_all_count = trade_get_all_count

# Model factory functions
class ModelFactory:
    """Factory for creating model instances with proper dependencies"""
    
    @staticmethod
    def create_trade_from_mt5(mt5_trade_data):
        """Create Trade instance from MT5 trade data"""
        from app.utils.calculators import safe_float_conversion
        
        return Trade(
            ticket_id=mt5_trade_data.get('ticket'),
            symbol=mt5_trade_data.get('symbol'),
            type=mt5_trade_data.get('type'),
            volume=safe_float_conversion(mt5_trade_data.get('volume')),
            entry_price=safe_float_conversion(mt5_trade_data.get('price_open')),
            current_price=safe_float_conversion(mt5_trade_data.get('price_current')),
            exit_price=safe_float_conversion(mt5_trade_data.get('price_close')),
            sl_price=safe_float_conversion(mt5_trade_data.get('sl')),
            tp_price=safe_float_conversion(mt5_trade_data.get('tp')),
            profit=safe_float_conversion(mt5_trade_data.get('profit')),
            commission=safe_float_conversion(mt5_trade_data.get('commission', 0)),
            swap=safe_float_conversion(mt5_trade_data.get('swap', 0)),
            comment=mt5_trade_data.get('comment', ''),
            magic_number=mt5_trade_data.get('magic', 0),
            entry_time=mt5_trade_data.get('time'),
            status='OPEN' if mt5_trade_data.get('profit') is None else 'CLOSED'
        )
    
    @staticmethod
    def create_user_with_defaults(username, password, email=None):
        """Create user with default preferences"""
        return User.create(username, password, email)
    
    @staticmethod
    def create_analytics_with_context():
        """Create Analytics instance with current app context"""
        return Analytics()

# Export utility classes
__all__.extend(['ModelUtils', 'ModelFactory', 'with_db_connection'])

# Initialize models when package is imported
def setup_models():
    """Setup models when package is imported"""
    try:
        # This will be called when models package is imported
        # Actual initialization happens in init_models with app context
        pass
    except:
        # Silently fail - proper initialization happens later
        pass

# Call setup on import
setup_models()