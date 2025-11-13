import os
import json
import hashlib
import uuid
import platform
import socket
import subprocess
from utils import add_log
from datetime import datetime, timedelta

class LicenseManager:
    def __init__(self):
        self.license_file = self.get_license_file_path()
        self.license_data = self.load_license()
        self.trial_days = 30

    def get_license_file_path(self):
        system = platform.system().lower()
        
        if system == "windows":
            license_dir = os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal', 'license')
        elif system == "darwin":
            license_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MT5Journal')
        else:
            license_dir = os.path.join(os.path.expanduser('~'), '.config', 'mt5journal', 'license')
        
        os.makedirs(license_dir, exist_ok=True)
        return os.path.join(license_dir, 'license.lic')

    def get_system_fingerprint(self):
        try:
            system_info = {
                'machine': platform.machine(),
                'processor': platform.processor(),
                'system': platform.system(),
                'node': platform.node(),
                'mac_address': self.get_mac_address()
            }
            
            fingerprint_str = ''.join(str(v) for v in system_info.values())
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
            
        except Exception as e:
            return str(uuid.uuid4())

    def get_mac_address(self):
        try:
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except:
            return "00:00:00:00:00:00"

    def load_license(self):
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
                    if self.validate_license_integrity(license_data):
                        return license_data
                    else:
                        add_log('WARNING', 'License file tampered with, resetting to trial', 'License')
                        return default_license
            else:
                self.save_license(default_license)
                return default_license
                
        except Exception as e:
            add_log('ERROR', f'License loading error: {e}', 'License')
            return default_license

    def save_license(self, license_data):
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            return True
        except Exception as e:
            add_log('ERROR', f'License saving error: {e}', 'License')
            return False

    def validate_license_integrity(self, license_data):
        try:
            required_fields = ['status', 'created_date', 'system_fingerprint']
            if not all(field in license_data for field in required_fields):
                return False
            
            current_fingerprint = self.get_system_fingerprint()
            if license_data.get('system_fingerprint') != current_fingerprint:
                add_log('WARNING', 'System fingerprint changed - possible license violation', 'License')
                return False
                
            return True
        except:
            return False

    def validate_license(self):
        try:
            if self.license_data['status'] == 'trial':
                expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
                if datetime.now() > expiry_date:
                    self.license_data['status'] = 'expired'
                    self.save_license(self.license_data)
                    return False, "Trial period has expired"
                return True, f"Trial active - {self.get_trial_days_left()} days remaining"
            
            elif self.license_data['status'] == 'licensed':
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
        try:
            expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
            days_left = (expiry_date - datetime.now()).days
            return max(0, days_left)
        except:
            return 0

    def validate_license_key(self, license_key):
        try:
            if not license_key or len(license_key) != 29:
                return False
            
            parts = license_key.split('-')
            if len(parts) != 4 or not all(len(part) == 7 for part in parts):
                return False
                
            return True
        except:
            return False

    def activate_license(self, license_key):
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
            'system_fingerprint': self.license_data.get('system_fingerprint')[:8] + '...'
        }

# Initialize license manager
license_manager = LicenseManager()