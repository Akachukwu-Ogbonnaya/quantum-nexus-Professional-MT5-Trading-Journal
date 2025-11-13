# app/utils/system_info.py
import os
import platform
import uuid
import hashlib

def detect_environment():
    """Enhanced environment detection for hybrid mode"""
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

def get_system_fingerprint():
    """Generate unique system fingerprint"""
    try:
        system_info = {
            'machine': platform.machine(),
            'processor': platform.processor(),
            'system': platform.system(),
            'node': platform.node(),
            'mac_address': get_mac_address()
        }
        
        fingerprint_str = ''.join(str(v) for v in system_info.values())
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
        
    except Exception as e:
        return str(uuid.uuid4())

def get_mac_address():
    """Get MAC address for system identification"""
    try:
        mac = uuid.getnode()
        return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
    except:
        return "00:00:00:00:00:00"

def get_platform_specific_config():
    """Get platform-specific configuration"""
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

def get_platform_info():
    """Get platform-specific information"""
    # Implementation from monolithic script
    pass