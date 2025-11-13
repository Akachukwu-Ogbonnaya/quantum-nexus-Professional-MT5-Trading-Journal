import sqlite3
from datetime import datetime, timedelta
import json

class License:
    def __init__(self, license_key=None, product_type='premium', customer_email=None, 
                 duration_days=365, max_activations=1, is_active=True):
        self.license_key = license_key
        self.product_type = product_type
        self.customer_email = customer_email
        self.duration_days = duration_days
        self.max_activations = max_activations
        self.is_active = is_active
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(days=duration_days)
    
    @staticmethod
    def init_db():
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                product_type TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                duration_days INTEGER DEFAULT 365,
                max_activations INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS license_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                system_fingerprint TEXT NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (license_key) REFERENCES licenses (license_key)
            )
        ''')
        conn.commit()
        conn.close()
    
    def save(self):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO licenses 
            (license_key, product_type, customer_email, duration_days, max_activations, is_active, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (self.license_key, self.product_type, self.customer_email, 
              self.duration_days, self.max_activations, self.is_active, self.expires_at))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_key(license_key):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM licenses WHERE license_key = ?', (license_key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            license = License(
                license_key=row[1],
                product_type=row[2],
                customer_email=row[3],
                duration_days=row[4],
                max_activations=row[5],
                is_active=bool(row[6])
            )
            license.created_at = row[7]
            license.expires_at = row[8]
            return license
        return None
    
    @staticmethod
    def get_all():
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM licenses ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        licenses = []
        for row in rows:
            license = License(
                license_key=row[1],
                product_type=row[2],
                customer_email=row[3],
                duration_days=row[4],
                max_activations=row[5],
                is_active=bool(row[6])
            )
            license.created_at = row[7]
            license.expires_at = row[8]
            licenses.append(license)
        return licenses
    
    def activate(self, system_fingerprint):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        
        # Check current activations
        cursor.execute('SELECT COUNT(*) FROM license_activations WHERE license_key = ? AND is_active = TRUE', 
                      (self.license_key,))
        current_activations = cursor.fetchone()[0]
        
        if current_activations >= self.max_activations:
            conn.close()
            return False, "Maximum activations reached"
        
        # Check if already activated on this system
        cursor.execute('SELECT id FROM license_activations WHERE license_key = ? AND system_fingerprint = ? AND is_active = TRUE',
                      (self.license_key, system_fingerprint))
        if cursor.fetchone():
            conn.close()
            return False, "Already activated on this system"
        
        # Create activation
        cursor.execute('''
            INSERT INTO license_activations (license_key, system_fingerprint) VALUES (?, ?)
        ''', (self.license_key, system_fingerprint))
        conn.commit()
        conn.close()
        return True, "License activated successfully"
    
    def deactivate(self, system_fingerprint):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE license_activations SET is_active = FALSE 
            WHERE license_key = ? AND system_fingerprint = ?
        ''', (self.license_key, system_fingerprint))
        conn.commit()
        conn.close()
        return True, "License deactivated"
    
    def is_valid(self, system_fingerprint=None):
        if not self.is_active:
            return False, "License is inactive"
        
        if datetime.now() > self.expires_at:
            return False, "License has expired"
        
        if system_fingerprint:
            conn = sqlite3.connect('licenses.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM license_activations 
                WHERE license_key = ? AND system_fingerprint = ? AND is_active = TRUE
            ''', (self.license_key, system_fingerprint))
            activation_exists = cursor.fetchone() is not None
            conn.close()
            
            if not activation_exists:
                return False, "License not activated on this system"
        
        return True, "License is valid"