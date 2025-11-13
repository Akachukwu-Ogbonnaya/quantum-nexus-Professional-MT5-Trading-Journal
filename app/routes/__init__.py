# app/routes/__init__.py
from flask import Blueprint, current_app, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required
import functools

# Import all route blueprints
from .auth import auth_bp
from .dashboard import dashboard_bp
from .analytics import analytics_bp
from .trading import trading_bp
from .trade_plan import trade_plan_bp
from .license import license_bp
from .desktop import desktop_bp
from .export import export_bp
from .api import api_bp

# List of all blueprints for easy registration
__all__ = [
    'auth_bp',
    'dashboard_bp', 
    'analytics_bp',
    'trading_bp',
    'trade_plan_bp',
    'license_bp',
    'desktop_bp',
    'export_bp',
    'api_bp'
]

def hybrid_compatible(route_func):
    """Decorator to make routes work in both web and desktop modes"""
    @functools.wraps(route_func)
    def wrapper(*args, **kwargs):
        try:
            return route_func(*args, **kwargs)
        except Exception as e:
            # Log the error
            current_app.logger.add_log('ERROR', f'Route {route_func.__name__} error: {e}', 'Routes')
            
            # Return appropriate response based on environment
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Operation failed', 'demo_mode': True})
            else:
                flash('Operation completed in demo mode', 'info')
                return redirect(request.referrer or url_for('dashboard.professional_dashboard'))
    return wrapper

def get_app_services():
    """Helper to get app services from current_app context"""
    return {
        'db_manager': current_app.db_manager,
        'config_manager': current_app.config_manager,
        'mt5_service': current_app.mt5_service,
        'sync_service': current_app.sync_service,
        'ai_service': current_app.ai_service,
        'license_service': current_app.license_service,
        'desktop_service': current_app.desktop_service,
        'socketio': current_app.socketio,
        'logger': current_app.logger
    }

def inject_services():
    """Inject services into route context"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            services = get_app_services()
            return f(services=services, *args, **kwargs)
        return decorated_function
    return decorator

# Route utility functions for templates
def format_currency(value):
    """Format currency for templates"""
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    return "$0.00"

def format_percent(value):
    """Format percentage for templates"""
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"
    return "0.00%"

def is_profitable(pnl):
    """Check if P&L is profitable"""
    return pnl > 0 if isinstance(pnl, (int, float)) else False

def calculate_planned_rr(trade):
    """Calculate planned risk/reward ratio"""
    try:
        if trade.get('planned_rr'):
            return float(trade['planned_rr'])
        return None
    except:
        return None

def calculate_actual_rr(trade):
    """Calculate actual risk/reward ratio"""
    try:
        if trade.get('actual_rr'):
            return float(trade['actual_rr'])
        return None
    except:
        return None

def calculate_trade_duration(trade):
    """Calculate trade duration"""
    try:
        if trade.get('duration'):
            return trade['duration']
        return None
    except:
        return None

def calculate_pnl_percent(trade):
    """Calculate P/L percentage"""
    try:
        if trade.get('profit') and trade.get('account_balance'):
            return (float(trade['profit']) / float(trade['account_balance'])) * 100
        return 0.0
    except:
        return 0.0

def get_trade_status(trade):
    """Get trade status"""
    try:
        return trade.get('status', 'UNKNOWN')
    except:
        return 'UNKNOWN'

# Export template helpers
template_helpers = {
    'format_currency': format_currency,
    'format_percent': format_percent,
    'is_profitable': is_profitable,
    'calculate_planned_rr': calculate_planned_rr,
    'calculate_actual_rr': calculate_actual_rr,
    'calculate_trade_duration': calculate_trade_duration,
    'calculate_pnl_percent': calculate_pnl_percent,
    'get_trade_status': get_trade_status
}

def register_template_helpers(app):
    """Register all template helpers with Flask app"""
    for name, helper in template_helpers.items():
        app.jinja_env.globals[name] = helper

# Route initialization function
def init_routes(app):
    """Initialize all routes with the Flask application"""
    
    # Register template helpers
    register_template_helpers(app)
    
    # Register all blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(trading_bp, url_prefix='/trading')
    app.register_blueprint(trade_plan_bp, url_prefix='/trade_plan')
    app.register_blueprint(license_bp, url_prefix='/license')
    app.register_blueprint(desktop_bp, url_prefix='/desktop')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register root routes (without prefix)
    @app.route('/')
    def index():
        """Professional home page"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.professional_dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.route('/quick/journal')
    @login_required
    def quick_journal():
        """Quick journal access"""
        return redirect(url_for('trading.journal'))
    
    @app.route('/quick/trade_plan')
    @login_required
    def quick_trade_plan():
        """Quick trade plan access"""
        return redirect(url_for('trade_plan.trade_plan'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.add_log('ERROR', f'Internal server error: {error}', 'Routes')
        return "Internal server error", 500
    
    # License middleware
    @app.before_request
    def check_license():
        """Check license status before each request"""
        # Skip license check for certain routes
        exempt_routes = [
            'static', 
            'auth.login', 
            'auth.register', 
            'auth.logout', 
            'api.validate_license',
            'license.license_management'
        ]
        
        if request.endpoint in exempt_routes:
            return
        
        # Check license status
        services = get_app_services()
        is_valid, message = services['license_service'].validate_license()
        
        if not is_valid:
            # Allow access to license management page even if expired
            if request.endpoint not in ['license.license_management', 'api.license_status', 'api.activate_license']:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'error': 'License required',
                        'message': message,
                        'redirect': url_for('license.license_management')
                    }), 402  # Payment Required
                else:
                    flash(f'⚠️ {message}. Please activate your license.', 'warning')
                    return redirect(url_for('license.license_management'))
    
    current_app.logger.add_log('INFO', 'Routes initialization completed', 'Routes')

# Export the initialization function
__all__.append('init_routes')