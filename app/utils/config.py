# app/utils/config.py
import os
import json
from .system_info import detect_environment
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