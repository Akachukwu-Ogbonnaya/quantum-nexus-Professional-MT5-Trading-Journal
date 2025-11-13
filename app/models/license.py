# models/license.py
import hashlib
import uuid
import platform
import socket
import subprocess
from datetime import datetime, timedelta
import json
import os
from app.utils.system_info import detect_environment  # ADDED: For environment detection

class LicenseManager:
    def __init__(self):
        self.license_file = self.get_license_file_path()
        self.license_data = self.load_license()
        self.trial_days = 30  # 30-day free trial
        
    def get_license_file_path(self):
        """Get license file path based on OS"""
        system = platform.system().lower()
        
        if system == "windows":
            license_dir = os.path.join(os.environ.get('APPDATA', ''), 'MT5Journal', 'license')
        elif system == "darwin":  # macOS
            license_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MT5Journal')
        else:  # Linux and other Unix-like
            license_dir = os.path.join(os.path.expanduser('~'), '.config', 'mt5journal', 'license')
        
        os.makedirs(license_dir, exist_ok=True)
        return os.path.join(license_dir, 'license.lic')
    
    def get_system_fingerprint(self):
        """Generate unique system fingerprint"""
        try:
            # Get system information
            system_info = {
                'machine': platform.machine(),
                'processor': platform.processor(),
                'system': platform.system(),
                'node': platform.node(),
                'mac_address': self.get_mac_address()
            }
            
            # Create hash from system info
            fingerprint_str = ''.join(str(v) for v in system_info.values())
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
            
        except Exception as e:
            # Fallback to random UUID if system info unavailable
            return str(uuid.uuid4())
    
    def get_mac_address(self):
        """Get MAC address for system identification"""
        try:
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except:
            return "00:00:00:00:00:00"
    
    def load_license(self):
        """Load license data from file"""
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
                    # Validate license integrity
                    if self.validate_license_integrity(license_data):
                        return license_data
                    else:
                        print('WARNING: License file tampered with, resetting to trial')
                        return default_license
            else:
                # Create initial trial license
                self.save_license(default_license)
                return default_license
                
        except Exception as e:
            print(f'ERROR: License loading error: {e}')
            return default_license
    
    def save_license(self, license_data):
        """Save license data to file"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            return True
        except Exception as e:
            print(f'ERROR: License saving error: {e}')
            return False
    
    def validate_license_integrity(self, license_data):
        """Validate license hasn't been tampered with"""
        try:
            required_fields = ['status', 'created_date', 'system_fingerprint']
            if not all(field in license_data for field in required_fields):
                return False
            
            # Check if system fingerprint matches
            current_fingerprint = self.get_system_fingerprint()
            if license_data.get('system_fingerprint') != current_fingerprint:
                print('WARNING: System fingerprint changed - possible license violation')
                return False
                
            return True
        except:
            return False
    
    def validate_license(self):
        """Validate current license status"""
        try:
            # Check if trial expired
            if self.license_data['status'] == 'trial':
                expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
                if datetime.now() > expiry_date:
                    self.license_data['status'] = 'expired'
                    self.save_license(self.license_data)
                    return False, "Trial period has expired"
                return True, f"Trial active - {self.get_trial_days_left()} days remaining"
            
            # Check if licensed
            elif self.license_data['status'] == 'licensed':
                # Validate license key
                if self.validate_license_key(self.license_data['license_key']):
                    return True, "License active"
                else:
                    return False, "Invalid license key"
            
            elif self.license_data['status'] == 'expired':
                return False, "License has expired"
                
            else:
                return False, "Invalid license status"
                
        except Exception as e:
            print(f'ERROR: License validation error: {e}')
            return False, "License validation error"
    
    def get_trial_days_left(self):
        """Get remaining trial days"""
        try:
            expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
            days_left = (expiry_date - datetime.now()).days
            return max(0, days_left)
        except:
            return 0
    
    def validate_license_key(self, license_key):
        """Validate license key format and signature"""
        try:
            if not license_key or len(license_key) != 29:
                return False
            
            # Simple validation - in production use proper cryptographic validation
            parts = license_key.split('-')
            if len(parts) != 4 or not all(len(part) == 7 for part in parts):
                return False
                
            return True
        except:
            return False
    
    def activate_license(self, license_key):
        """Activate a license key"""
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
                    print(f'INFO: License activated successfully: {license_key}')
                    return True, "License activated successfully!"
                else:
                    return False, "Failed to save license"
            else:
                return False, "Invalid license key format"
                
        except Exception as e:
            print(f'ERROR: License activation error: {e}')
            return False, f"Activation error: {str(e)}"
    
    def get_license_info(self):
        """Get comprehensive license information"""
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
            'system_fingerprint': self.license_data.get('system_fingerprint')[:8] + '...'  # Partial for security
        }

    def get_application_mode(self):
        """Get application mode based on environment"""
        environment = detect_environment()
        return {
            'environment': environment,
            'is_desktop': environment == 'sqlite',
            'is_web': environment == 'postgresql'
        }

class License:
    def __init__(self, license_data=None):
        self.license_data = license_data or {}
        self.manager = LicenseManager()
    
    @staticmethod
    def create_trial_license():
        """Create a new trial license"""
        manager = LicenseManager()
        return License(manager.license_data)
    
    def is_valid(self):
        """Check if license is valid"""
        is_valid, message = self.manager.validate_license()
        return is_valid
    
    def get_status(self):
        """Get license status"""
        return self.license_data.get('status', 'trial')
    
    def get_features(self):
        """Get available features based on license"""
        return self.license_data.get('features', [])
    
    def has_feature(self, feature):
        """Check if license includes specific feature"""
        return feature in self.get_features()
    
    def is_trial(self):
        """Check if license is in trial period"""
        return self.get_status() == 'trial'
    
    def is_licensed(self):
        """Check if license is fully licensed"""
        return self.get_status() == 'licensed'
    
    def is_expired(self):
        """Check if license has expired"""
        return self.get_status() == 'expired'
    
    def get_remaining_days(self):
        """Get remaining trial days"""
        return self.manager.get_trial_days_left()
    
    def to_dict(self):
        """Convert license to dictionary"""
        return self.manager.get_license_info()

    def get_application_context(self):
        """Get license context for application"""
        license_info = self.to_dict()
        license_info.update(self.manager.get_application_mode())
        return license_info