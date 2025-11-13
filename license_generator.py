import secrets
import string
from datetime import datetime
from app.models.license import License

class LicenseGenerator:
    @staticmethod
    def generate_license_key(product_type="premium"):
        """Generate license key in format: XXXX-XXXX-XXXX-XXXX"""
        characters = string.ascii_uppercase + string.digits
        key_parts = []
        
        for i in range(4):
            part = ''.join(secrets.choice(characters) for _ in range(4))
            key_parts.append(part)
        
        license_key = '-'.join(key_parts)
        
        # Add product type prefix
        prefixes = {'basic': 'BSC', 'premium': 'PRM', 'professional': 'PRO'}
        prefix = prefixes.get(product_type, 'LIC')
        license_key = f"{prefix}-{license_key}"
        
        return license_key
    
    @staticmethod
    def create_license(product_type, customer_email, duration_days=365, max_activations=1):
        license_key = LicenseGenerator.generate_license_key(product_type)
        
        license = License(
            license_key=license_key,
            product_type=product_type,
            customer_email=customer_email,
            duration_days=duration_days,
            max_activations=max_activations
        )
        
        license.save()
        return license