# app/utils/system_info.py
import os
import platform
import uuid
import hashlib
import socket
from datetime import datetime

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
    try:
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture()[0],
            'node': platform.node(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'hostname': socket.gethostname(),
            'timestamp': datetime.now().isoformat(),
            'environment': detect_environment(),
            'is_container': os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'),
            'cwd': os.getcwd(),
            'user': os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
        }
    except Exception as e:
        # Return minimal information if platform calls fail
        return {
            'system': 'Unknown',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'environment': detect_environment()
        }

def get_mt5_connection_status():
    """Get MT5 connection status for hybrid compatibility"""
    # This is a placeholder for container/desktop environments without MT5
    # In a real desktop environment with MT5 installed, this would check actual connection
    
    # Check if we're in a container (Docker) environment
    is_container = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
    
    if is_container:
        return {
            "connected": False,
            "error": "MT5 is not available in container environment",
            "demo_mode": True,
            "environment": "container",
            "timestamp": datetime.now().isoformat(),
            "recommendation": "Use desktop installation for MT5 integration",
            "terminal_path": None,
            "account": None,
            "server": None,
            "balance": 0.0,
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "positions_count": 0,
            "orders_count": 0
        }
    else:
        # For desktop environments, try to detect MT5
        # This is simplified - real implementation would attempt MT5 connection
        return {
            "connected": False,
            "error": "MT5 not detected or not configured",
            "demo_mode": True,
            "environment": "desktop",
            "timestamp": datetime.now().isoformat(),
            "recommendation": "Install MetaTrader 5 and configure connection",
            "terminal_path": get_platform_specific_config().get('terminal_path'),
            "account": None,
            "server": None,
            "balance": 0.0,
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "positions_count": 0,
            "orders_count": 0
        }

def should_reset_database():
    """
    Determine if database should be reset based on environment and conditions
    
    Returns True if database reset is recommended, False otherwise
    """
    try:
        environment = detect_environment()
        
        # In PostgreSQL/web mode, never reset automatically
        if environment == 'postgresql':
            return False
        
        # In SQLite/desktop mode, check for common reset conditions
        sqlite_conditions = [
            # Check for database corruption
            'DATABASE_RESET' in os.environ and os.environ['DATABASE_RESET'].lower() == 'true',
            # Development mode reset
            'FLASK_ENV' in os.environ and os.environ['FLASK_ENV'] == 'development',
            # Check if database file exists but is empty/corrupted
            not os.path.exists(os.path.join('database', 'quantum_journal.db')) or 
            os.path.getsize(os.path.join('database', 'quantum_journal.db')) == 0
        ]
        
        return any(sqlite_conditions)
        
    except Exception as e:
        # If we can't determine, don't reset
        return False

# Export all functions
__all__ = [
    'detect_environment',
    'get_system_fingerprint',
    'get_mac_address',
    'get_platform_specific_config',
    'get_platform_info',
    'get_mt5_connection_status',
    'should_reset_database'
]

# Initialize system info
system_info = {
    'environment': detect_environment(),
    'platform': get_platform_info(),
    'platform_config': get_platform_specific_config(),
    'fingerprint': get_system_fingerprint(),
    'mt5_status': get_mt5_connection_status()
}
