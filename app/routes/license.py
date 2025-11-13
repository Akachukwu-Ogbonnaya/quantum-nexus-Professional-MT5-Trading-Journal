from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app.utils.license import license_manager
from app.utils.logging import add_log

license_bp = Blueprint('license', __name__)

@license_bp.route('/license', methods=['GET', 'POST'])
@login_required
def license_management():
    """License management page"""
    license_info = license_manager.get_license_info()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'activate_license':
            license_key = request.form.get('license_key', '').strip().upper()
            if license_key:
                success, message = license_manager.activate_license(license_key)
                if success:
                    flash(f'✅ {message}', 'success')
                else:
                    flash(f'❌ {message}', 'danger')
            else:
                flash('❌ Please enter a license key', 'danger')
                
        elif action == 'extend_trial':
            # For demo purposes - in production this would require payment
            flash('ℹ️ Trial extension requires license purchase', 'info')
    
    return render_template('license.html', 
                         license_info=license_info,
                         current_year=datetime.now().year)

@license_bp.route('/api/license/status')
@login_required
def api_license_status():
    """API endpoint for license status"""
    return jsonify(license_manager.get_license_info())

@license_bp.route('/api/license/activate', methods=['POST'])
@login_required
def api_activate_license():
    """API endpoint for license activation"""
    data = request.get_json()
    license_key = data.get('license_key', '').strip().upper()
    
    if license_key:
        success, message = license_manager.activate_license(license_key)
        return jsonify({'success': success, 'message': message})
    else:
        return jsonify({'success': False, 'message': 'No license key provided'})

@license_bp.route('/api/license/validate')
def api_validate_license():
    """API endpoint for license validation (public)"""
    is_valid, message = license_manager.validate_license()
    return jsonify({
        'valid': is_valid,
        'message': message,
        'trial_days_left': license_manager.get_trial_days_left()
    })