from flask import Blueprint, request, jsonify
from app.services.payment_processor import PaymentProcessor
from app.services.license_generator import LicenseGenerator
from config import Config

webhooks_bp = Blueprint('webhooks', __name__)
payment_processor = PaymentProcessor(Config.STRIPE_SECRET_KEY)

@webhooks_bp.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        success, result = payment_processor.handle_webhook(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
        
        if success:
            return jsonify({'success': True, 'license_key': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400