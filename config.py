import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///licenses.db')
    
    # License Settings
    LICENSE_TIERS = {
        'basic': {'price': 49, 'duration': 365, 'max_activations': 1},
        'premium': {'price': 99, 'duration': 365, 'max_activations': 3},
        'professional': {'price': 199, 'duration': 365, 'max_activations': 5}
    }
    
    # Stripe
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Admin
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')