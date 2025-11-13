import os
import platform
import sys
from utils.config import config
from utils.database import detect_environment
from utils import add_log
from datetime import datetime

def setup_desktop_environment():
    if detect_environment() == 'sqlite':
        desktop_dirs = [
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'exports'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'backups'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'reports')
        ]
        
        for directory in desktop_dirs:
            os.makedirs(directory, exist_ok=True)
        
        config.setdefault('desktop', {})
        config['desktop'].update({
            'auto_start': False,
            'minimize_to_tray': True,
            'start_with_windows': False,
            'export_directory': desktop_dirs[0],
            'backup_directory': desktop_dirs[1]
        })
        
        print("✅ Desktop environment configured")

def get_platform_specific_config():
    system = platform.system().lower()
    
    config = {
        'windows': {
            'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
            'data_dir': os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal'),
            'backup_dir': os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'MT5Journal', 'backups')
        },
        'darwin': {
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
    
    return config.get(system, config['windows'])

def setup_auto_start():
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

def setup_macos_auto_start():
    add_log('INFO', 'macOS auto-start configuration not implemented', 'Desktop')

def setup_linux_auto_start():
    add_log('INFO', 'Linux auto-start configuration not implemented', 'Desktop')

def get_hybrid_config_path():
    environment = detect_environment()
    
    if environment == 'postgresql':
        return "config.json"
    else:
        if os.name == 'nt':
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal')
        else:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'mt5journal')
        
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

def initialize_hybrid_config():
    environment = detect_environment()
    
    return {
        'mt5': {
            'server': '',
            'account': 0,
            'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
            'password': ''
        },
        'environment': environment,
        'created_at': datetime.now().isoformat(),
        'hybrid_mode': True
    }