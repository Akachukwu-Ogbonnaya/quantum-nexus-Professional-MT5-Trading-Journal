from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import sqlite3
from app.models.license import License
from app.services.license_generator import LicenseGenerator

admin_bp = Blueprint('admin', __name__)

# Simple admin authentication
ADMIN_CREDENTIALS = {'username': 'admin', 'password': 'admin123'}

def check_admin_auth():
    """Check if user is authenticated as admin"""
    # Simple session check - in production use proper sessions
    return request.cookies.get('admin_authenticated') == 'true'

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            response = redirect(url_for('admin.admin_dashboard'))
            response.set_cookie('admin_authenticated', 'true')
            return response
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    if not check_admin_auth():
        return redirect(url_for('admin.admin_login'))
    
    # Get license statistics
    conn = sqlite3.connect('licenses.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM licenses')
    total_licenses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM licenses WHERE is_active = TRUE')
    active_licenses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM license_activations WHERE is_active = TRUE')
    total_activations = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                         total_licenses=total_licenses,
                         active_licenses=active_licenses,
                         total_activations=total_activations)

@admin_bp.route('/admin/licenses')
def license_manager():
    if not check_admin_auth():
        return redirect(url_for('admin.admin_login'))
    
    licenses = License.get_all()
    return render_template('admin/license_manager.html', licenses=licenses)

@admin_bp.route('/admin/licenses/create', methods=['POST'])
def create_license():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    product_type = data.get('product_type', 'premium')
    customer_email = data.get('customer_email')
    duration_days = data.get('duration_days', 365)
    
    if not customer_email:
        return jsonify({'error': 'Customer email required'}), 400
    
    license_obj = LicenseGenerator.create_license(
        product_type=product_type,
        customer_email=customer_email,
        duration_days=duration_days
    )
    
    return jsonify({
        'success': True,
        'license_key': license_obj.license_key,
        'customer_email': customer_email
    })

@admin_bp.route('/admin/licenses/<license_key>/deactivate', methods=['POST'])
def deactivate_license(license_key):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('licenses.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE licenses SET is_active = FALSE WHERE license_key = ?', (license_key,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'License deactivated'})