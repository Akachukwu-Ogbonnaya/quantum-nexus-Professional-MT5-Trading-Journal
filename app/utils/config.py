# app/utils/config.py
import os
import json
from .system_info import detect_environment

# =============================================================================
# ADD MISSING FUNCTIONS
# =============================================================================
def get_hybrid_config_path():
    """Get the hybrid configuration path for the current environment"""
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Try to detect environment, but if it fails, use SQLite mode as default
    try:
        environment = detect_environment()
        if environment == 'postgresql':
            # For web/PostgreSQL mode, config is in app root
            return os.path.join(app_root, "config.json")
    except:
        pass
    
    # Default to SQLite/desktop mode
    database_dir = os.path.join(app_root, "database")
    os.makedirs(database_dir, exist_ok=True)
    return os.path.join(database_dir, "config.json")

def initialize_hybrid_config():
    """Initialize hybrid configuration for current environment"""
    config_path = get_hybrid_config_path()
    return ConfigManager(config_path)

def validate_csrf(token):
    """Validate CSRF token (simplified version)"""
    # This is a placeholder - in production, you'd have proper CSRF validation
    if not token or len(token) < 10:
        return False
    return True

class ConfigManager:
    def __init__(self, config_path=None):
        # If no path provided, use hybrid config path
        if not config_path:
            config_path = get_hybrid_config_path()
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
try:
    # Use config_manager's path, not hardcoded "config.json"
    with open(config_manager.config_path, "r") as f:
        config = json.load(f)

    # ENSURE SYNC SECTION EXISTS
    if 'sync' not in config:
        config['sync'] = {
            'auto_sync_interval': 300,
            'days_history': 90,
            'real_time_updates': True
        }
        # Save the updated config
        with open(config_manager.config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"✅ Added missing 'sync' section to {config_manager.config_path}")

    # Ensure all required sections exist
    required_sections = ['database', 'ui']
    for section in required_sections:
        if section not in config:
            config[section] = {}
            print(f"✅ Added missing '{section}' section to config")

except Exception as e:
    print(f"⚠️ Config reload warning: {e}")

# =============================================================================
# ADDITIONAL HELPER FUNCTIONS FOR COMPATIBILITY
# =============================================================================
def get_config():
    """Get current config (alias for config_manager.config)"""
    return config_manager.config

def save_config():
    """Save current config to file"""
    try:
        with open(config_manager.config_path, "w") as f:
            json.dump(config_manager.config, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def update_config(section, key, value):
    """Update a specific config value"""
    try:
        if section not in config_manager.config:
            config_manager.config[section] = {}
        config_manager.config[section][key] = value
        return save_config()
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False
