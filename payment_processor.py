import stripe
from app.services.license_generator import LicenseGenerator

class PaymentProcessor:
    def __init__(self, stripe_secret_key):
        self.stripe_secret_key = stripe_secret_key
        stripe.api_key = stripe_secret_key
    
    def create_checkout_session(self, product_type, customer_email, success_url, cancel_url):
        """Create Stripe checkout session"""
        prices = {
            'basic': {'price': 4900, 'name': 'Basic License'},  # $49.00
            'premium': {'price': 9900, 'name': 'Premium License'},  # $99.00
            'professional': {'price': 19900, 'name': 'Professional License'}  # $199.00
        }
        
        product = prices.get(product_type)
        if not product:
            raise ValueError(f"Unknown product type: {product_type}")
        
        try:
            session = stripe.checkout.Session.create(
                customer_email=customer_email,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product['name'],
                            'description': f'{product_type.upper()} license for MT5 Trading Journal'
                        },
                        'unit_amount': product['price'],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'product_type': product_type,
                    'customer_email': customer_email
                }
            )
            return session.id
        except Exception as e:
            print(f"Stripe error: {e}")
            return None
    
    def handle_webhook(self, payload, sig_header, webhook_secret):
        """Handle Stripe webhook for successful payments"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                
                # Create license for customer
                product_type = session['metadata']['product_type']
                customer_email = session['metadata']['customer_email']
                
                license_obj = LicenseGenerator.create_license(
                    product_type=product_type,
                    customer_email=customer_email
                )
                
                print(f"Created license {license_obj.license_key} for {customer_email}")
                return True, license_obj.license_key
            
            return False, "Unhandled event type"
        except Exception as e:
            return False, str(e)