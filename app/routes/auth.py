from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from app.models import User
from app.utils.logging import add_log

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Professional home page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.professional_dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Professional login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.professional_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.get_by_username(username)
        if user is None:
            # Auto-create user for demo (professional feature)
            user = User.create(username, password)
            if user:
                add_log('INFO', f'Auto-created professional user: {username}', 'Auth')
                flash('Account created successfully!', 'success')

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.update_last_login()
            add_log('INFO', f'Professional user logged in: {username}', 'Auth')

            # Initial professional sync
            from app.utils.sync import data_synchronizer
            import threading
            threading.Thread(target=data_synchronizer.sync_with_mt5, daemon=True).start()

            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard.professional_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Professional registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.professional_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')

        existing_user = User.get_by_username(username)
        if existing_user:
            flash('Username already exists', 'warning')
            return render_template('register.html')

        user = User.create(username, password, email)
        if user:
            login_user(user)
            add_log('INFO', f'New professional user registered: {username}', 'Auth')
            flash('Registration successful! Welcome to Professional MT5 Journal.', 'success')
            return redirect(url_for('dashboard.professional_dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Professional logout"""
    username = current_user.username
    logout_user()
    add_log('INFO', f'User logged out: {username}', 'Auth')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/enter_password', methods=['GET', 'POST'])
@login_required
def enter_password():
    """Enter password for MT5 connection"""
    from app.utils.config import get_hybrid_config_path, initialize_hybrid_config
    import json
    from datetime import datetime
    
    # Load saved settings with hybrid path
    try:
        config_path = get_hybrid_config_path()
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = initialize_hybrid_config()

    if request.method == 'POST':
        password = request.form.get('password')
        from app.utils.environment import detect_environment
        environment = detect_environment()

        if password:
            # Test connection with entered password
            mt5_config = config_data.get('mt5', {})
            if all(k in mt5_config for k in ['account', 'server']):
                from app.mt5.manager import mt5_manager
                success = mt5_manager.initialize_connection(
                    mt5_config['account'],
                    password,
                    mt5_config['server'],
                    mt5_config.get('terminal_path', '')
                )

                if success:
                    # Store password in session (encrypted by Flask)
                    session['mt5_authenticated'] = True
                    session['mt5_password'] = password  # Temporary session storage
                    
                    # Environment-specific message
                    if environment == 'sqlite':
                        flash('✅ Password accepted! MT5 connected in Desktop Mode.', 'success')
                    else:
                        flash('✅ Password accepted! MT5 connected in Web Mode.', 'success')
                        
                    return redirect('/configuration')
                else:
                    # Hybrid-aware error
                    if environment == 'postgresql':
                        flash('⚠️ Web mode: Using demo data. Live connection not required.', 'info')
                    else:
                        flash('❌ Connection failed. Check password and try again.', 'danger')
            else:
                flash('No MT5 configuration found. Please set up server and account first.', 'danger')

    return render_template('enter_password.html',
                           config=config_data.get('mt5', {}))