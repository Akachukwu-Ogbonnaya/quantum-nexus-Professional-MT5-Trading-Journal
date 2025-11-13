# app/utils/__init__.py
import os
import sys
import platform
import json
import sqlite3
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import pandas as pd
import numpy as np
import hashlib
import uuid
import socket
import subprocess
from flask import current_app

# Import all utility modules
from .database import (
    HybridDatabaseManager, 
    get_db_connection, 
    universal_execute, 
    conn_fetch_dataframe,
    init_database,
    get_universal_connection,
    DatabaseMigrator
)

from .calculators import (
    safe_float_conversion,
    calculate_risk_reward,
    calculate_trade_duration,
    calculate_position_size,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_recovery_factor,
    calculate_expectancy,
    calculate_kelly_criterion,
    calculate_consecutive_streaks,
    calculate_account_change_percent,
    ProfessionalTradingCalculator
)

from .config import (
    ConfigManager,
    get_hybrid_config_path,
    initialize_hybrid_config,
    validate_csrf
)

from .system_info import (
    detect_environment,
    get_platform_specific_config,
    get_platform_info,
    get_mt5_connection_status,
    should_reset_database
)

from .installer import (
    setup_desktop_environment,
    setup_auto_start,
    setup_windows_auto_start,
    setup_macos_auto_start,
    setup_linux_auto_start,
    create_desktop_shortcut,
    install_dependencies
)

# Export all utilities for easy access
__all__ = [
    # Database utilities
    'HybridDatabaseManager',
    'get_db_connection', 
    'universal_execute',
    'conn_fetch_dataframe',
    'init_database',
    'get_universal_connection',
    'DatabaseMigrator',
    
    # Calculator utilities
    'safe_float_conversion',
    'calculate_risk_reward',
    'calculate_trade_duration', 
    'calculate_position_size',
    'calculate_max_drawdown',
    'calculate_sharpe_ratio',
    'calculate_recovery_factor',
    'calculate_expectancy',
    'calculate_kelly_criterion',
    'calculate_consecutive_streaks',
    'calculate_account_change_percent',
    'ProfessionalTradingCalculator',
    
    # Configuration utilities
    'ConfigManager',
    'get_hybrid_config_path',
    'initialize_hybrid_config', 
    'validate_csrf',
    
    # System info utilities
    'detect_environment',
    'get_platform_specific_config',
    'get_platform_info',
    'get_mt5_connection_status',
    'should_reset_database',
    
    # Installer utilities
    'setup_desktop_environment',
    'setup_auto_start',
    'setup_windows_auto_start',
    'setup_macos_auto_start',
    'setup_linux_auto_start',
    'create_desktop_shortcut',
    'install_dependencies'
]

# Utility initialization manager
class UtilityManager:
    """Manages initialization and coordination of all utility modules"""
    
    def __init__(self, app=None):
        self.app = app
        self.initialized = False
        self.utilities = {}
        
    def initialize_utilities(self, config_path="config.json"):
        """Initialize all utility modules"""
        try:
            # Initialize configuration manager
            self.utilities['config'] = ConfigManager(config_path)
            config = self.utilities['config'].config
            
            # Initialize database manager
            self.utilities['database'] = HybridDatabaseManager()
            
            # Initialize calculators
            self.utilities['calculators'] = ProfessionalTradingCalculator()
            
            # Initialize system info
            self.utilities['system_info'] = {
                'environment': detect_environment(),
                'platform': get_platform_info(),
                'platform_config': get_platform_specific_config()
            }
            
            # Initialize installer utilities
            self.utilities['installer'] = {
                'desktop_setup': setup_desktop_environment,
                'auto_start': setup_auto_start,
                'create_shortcut': create_desktop_shortcut
            }
            
            self.initialized = True
            
            if self.app:
                self.app.logger.add_log('INFO', 'Utilities initialized successfully', 'UtilityManager')
            
        except Exception as e:
            if self.app:
                self.app.logger.add_log('ERROR', f'Utility initialization failed: {e}', 'UtilityManager')
            raise
    
    def get_utility(self, utility_type):
        """Get a specific utility by type"""
        return self.utilities.get(utility_type)
    
    def get_database_manager(self):
        """Get database manager utility"""
        return self.utilities.get('database')
    
    def get_config_manager(self):
        """Get configuration manager utility"""
        return self.utilities.get('config')
    
    def get_calculator(self):
        """Get trading calculator utility"""
        return self.utilities.get('calculators')
    
    def get_system_info(self):
        """Get system information utility"""
        return self.utilities.get('system_info', {})

# Data conversion utilities
class DataConverter:
    """Utilities for data conversion and formatting"""
    
    @staticmethod
    def adapt_date_iso(val):
        """Adapt datetime.date to ISO 8601 date."""
        return val.isoformat()

    @staticmethod
    def adapt_datetime_iso(val):
        """Adapt datetime.datetime to timezone-naive ISO 8601 datetime."""
        return val.isoformat()

    @staticmethod
    def convert_date(val):
        """Convert ISO 8601 date to datetime.date object."""
        return datetime.fromisoformat(val.decode())

    @staticmethod
    def convert_datetime(val):
        """Convert ISO 8601 datetime to datetime.datetime object."""
        return datetime.fromisoformat(val.decode())
    
    @staticmethod
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
    
    @staticmethod
    def dataframe_to_dict_list(df):
        """Convert DataFrame to list of dictionaries"""
        if df.empty:
            return []
        return df.to_dict('records')
    
    @staticmethod
    def dict_list_to_dataframe(data_list):
        """Convert list of dictionaries to DataFrame"""
        if not data_list:
            return pd.DataFrame()
        return pd.DataFrame(data_list)

# File and path utilities
class PathManager:
    """Utilities for file and path management"""
    
    @staticmethod
    def ensure_directory(path):
        """Ensure directory exists, create if it doesn't"""
        os.makedirs(path, exist_ok=True)
        return path
    
    @staticmethod
    def get_application_root():
        """Get application root directory"""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    @staticmethod
    def get_database_path():
        """Get database path based on environment"""
        environment = detect_environment()
        if environment == 'postgresql':
            return None  # PostgreSQL uses connection string
        else:
            db_path = os.path.join(PathManager.get_application_root(), "database", "quantum_journal.db")
            PathManager.ensure_directory(os.path.dirname(db_path))
            return db_path
    
    @staticmethod
    def get_logs_directory():
        """Get logs directory path"""
        logs_dir = os.path.join(PathManager.get_application_root(), "logs")
        return PathManager.ensure_directory(logs_dir)
    
    @staticmethod
    def get_exports_directory():
        """Get exports directory path"""
        exports_dir = os.path.join(PathManager.get_application_root(), "exports")
        return PathManager.ensure_directory(exports_dir)
    
    @staticmethod
    def get_backups_directory():
        """Get backups directory path"""
        backups_dir = os.path.join(PathManager.get_application_root(), "database", "backups")
        return PathManager.ensure_directory(backups_dir)

# Error handling utilities
class ErrorHandler:
    """Utilities for error handling and recovery"""
    
    @staticmethod
    def handle_database_error(error, context="Database operation"):
        """Handle database errors appropriately for environment"""
        environment = detect_environment()
        
        if environment == 'postgresql':
            # For web: Log and return JSON error
            if current_app:
                current_app.logger.add_log('ERROR', f'{context} failed: {error}', 'Database')
            return {'success': False, 'error': 'Database operation failed'}
        else:
            # For desktop: Attempt recovery or use demo data
            if current_app:
                current_app.logger.add_log('WARNING', f'{context} failed, using demo data: {error}', 'Database')
            return {'success': True, 'demo_mode': True, 'message': 'Using demo data'}
    
    @staticmethod
    def hybrid_compatible(route_func):
        """Decorator to make functions work in both web and desktop modes"""
        import functools
        
        @functools.wraps(route_func)
        def wrapper(*args, **kwargs):
            try:
                return route_func(*args, **kwargs)
            except Exception as e:
                # Log the error
                if current_app:
                    current_app.logger.add_log('ERROR', f'Route {route_func.__name__} error: {e}', 'Hybrid')
                
                # Return appropriate response based on environment
                from flask import request, jsonify, redirect, url_for, flash
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Operation failed', 'demo_mode': True})
                else:
                    flash('Operation completed in demo mode', 'info')
                    return redirect(request.referrer or url_for('professional_dashboard'))
        return wrapper
    
    @staticmethod
    def safe_execute(func, default_return=None, error_context="Operation"):
        """Safely execute a function with error handling"""
        try:
            return func()
        except Exception as e:
            if current_app:
                current_app.logger.add_log('ERROR', f'{error_context} failed: {e}', 'SafeExecute')
            return default_return

# Formatting utilities
class Formatter:
    """Utilities for data formatting and presentation"""
    
    @staticmethod
    def format_currency(value):
        """Format value as currency"""
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return "$0.00"
    
    @staticmethod
    def format_percent(value):
        """Format value as percentage"""
        if isinstance(value, (int, float)):
            return f"{value:.2f}%"
        return "0.00%"
    
    @staticmethod
    def format_duration(seconds):
        """Format duration in seconds to human readable format"""
        if not seconds:
            return "N/A"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h"
    
    @staticmethod
    def format_timestamp(timestamp, format_str="%Y-%m-%d %H:%M:%S"):
        """Format timestamp to string"""
        if not timestamp:
            return "N/A"
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return timestamp
        
        if isinstance(timestamp, datetime):
            return timestamp.strftime(format_str)
        
        return str(timestamp)

# Validation utilities
class Validator:
    """Utilities for data validation"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) if email else False
    
    @staticmethod
    def validate_license_key(license_key):
        """Validate license key format"""
        try:
            if not license_key or len(license_key) != 29:
                return False
            
            parts = license_key.split('-')
            if len(parts) != 4 or not all(len(part) == 7 for part in parts):
                return False
                
            return True
        except:
            return False
    
    @staticmethod
    def validate_trade_data(trade_data):
        """Validate trade data structure"""
        required_fields = ['symbol', 'type', 'volume', 'entry_price']
        for field in required_fields:
            if field not in trade_data or not trade_data[field]:
                return False, f"Missing required field: {field}"
        
        if trade_data['volume'] <= 0:
            return False, "Volume must be positive"
        
        if trade_data['entry_price'] <= 0:
            return False, "Entry price must be positive"
        
        return True, "Valid"

# Export additional utility classes
__all__.extend([
    'UtilityManager',
    'DataConverter',
    'PathManager', 
    'ErrorHandler',
    'Formatter',
    'Validator'
])

# Utility initialization function
def init_utilities(app, config_path="config.json"):
    """Initialize all utilities with the application"""
    
    # Create utility manager
    utility_manager = UtilityManager(app)
    app.utility_manager = utility_manager
    
    # Initialize all utilities
    utility_manager.initialize_utilities(config_path)
    
    # Register SQLite3 date adapters for Python 3.12+
    try:
        sqlite3.register_adapter(datetime, DataConverter.adapt_datetime_iso)
        sqlite3.register_adapter(datetime.date, DataConverter.adapt_date_iso)
        sqlite3.register_converter("date", DataConverter.convert_date)
        sqlite3.register_converter("datetime", DataConverter.convert_datetime)
    except Exception as e:
        app.logger.add_log('WARNING', f'SQLite date adapter registration failed: {e}', 'Utilities')
    
    app.logger.add_log('INFO', 'Utilities initialization completed', 'Utilities')
    return utility_manager

# Global utility access functions
def get_database_manager():
    """Get database manager from current app context"""
    if hasattr(current_app, 'utility_manager'):
        return current_app.utility_manager.get_database_manager()
    return HybridDatabaseManager()

def get_config_manager():
    """Get configuration manager from current app context"""
    if hasattr(current_app, 'utility_manager'):
        return current_app.utility_manager.get_config_manager()
    return ConfigManager()

def get_calculator():
    """Get trading calculator from current app context"""
    if hasattr(current_app, 'utility_manager'):
        return current_app.utility_manager.get_calculator()
    return ProfessionalTradingCalculator()

def get_system_info():
    """Get system information from current app context"""
    if hasattr(current_app, 'utility_manager'):
        return current_app.utility_manager.get_system_info()
    return {
        'environment': detect_environment(),
        'platform': get_platform_info()
    }

# Export global access functions
__all__.extend([
    'init_utilities',
    'get_database_manager',
    'get_config_manager', 
    'get_calculator',
    'get_system_info'
])

# Initialize on import
def setup_utilities():
    """Setup utilities when package is imported"""
    try:
        # Register SQLite date adapters
        sqlite3.register_adapter(datetime, DataConverter.adapt_datetime_iso)
        sqlite3.register_adapter(datetime.date, DataConverter.adapt_date_iso)
        sqlite3.register_converter("date", DataConverter.convert_date)
        sqlite3.register_converter("datetime", DataConverter.convert_datetime)
    except:
        pass  # Silently fail - will be reinitialized with app context

# Call setup on import
setup_utilities()