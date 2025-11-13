from flask import Blueprint, request, jsonify
from app.models.license import License

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    
    license_key = data.get('license_key')
    system_fingerprint = data.get('system_fingerprint')
    
    if not license_key:
        return jsonify({'valid': False, 'error': 'License key required'}), 400
    
    license_obj = License.get_by_key(license_key)
    if not license_obj:
        return jsonify({'valid': False, 'error': 'License not found'}), 404
    
    is_valid, message = license_obj.is_valid(system_fingerprint)
    
    response_data = {
        'valid': is_valid,
        'message': message,
        'license': {
            'key': license_obj.license_key,
            'product_type': license_obj.product_type,
            'customer_email': license_obj.customer_email,
            'is_active': license_obj.is_active,
            'expires_at': license_obj.expires_at.isoformat() if license_obj.expires_at else None
        }
    }
    
    return jsonify(response_data)

@api_bp.route('/api/activate', methods=['POST'])
def activate_license():
    data = request.get_json()
    
    license_key = data.get('license_key')
    system_fingerprint = data.get('system_fingerprint')
    
    if not license_key or not system_fingerprint:
        return jsonify({'success': False, 'error': 'License key and system fingerprint required'}), 400
    
    license_obj = License.get_by_key(license_key)
    if not license_obj:
        return jsonify({'success': False, 'error': 'License not found'}), 404
    
    success, message = license_obj.activate(system_fingerprint)
    
    return jsonify({'success': success, 'message': message})

@api_bp.route('/api/deactivate', methods=['POST'])
def deactivate_license():
    data = request.get_json()
    
    license_key = data.get('license_key')
    system_fingerprint = data.get('system_fingerprint')
    
    if not license_key or not system_fingerprint:
        return jsonify({'success': False, 'error': 'License key and system fingerprint required'}), 400
    
    license_obj = License.get_by_key(license_key)
    if not license_obj:
        return jsonify({'success': False, 'error': 'License not found'}), 404
    
    success, message = license_obj.deactivate(system_fingerprint)
    
    return jsonify({'success': success, 'message': message})