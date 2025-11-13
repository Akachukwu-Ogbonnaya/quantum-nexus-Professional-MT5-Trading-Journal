# app/__init__.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

from flask import Flask
from flask_session import Session
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_socketio import SocketIO

# Import configuration
from app.utils.config import ConfigManager

# Import models for initialization
from app.models.user import User
from app.models.trade import Trade
from app.models.analytics import Analytics
from app.models.license import LicenseManager

# Import services
from app.services.mt5_service import MT5Service
from app.services.sync_service import SyncService
from app.services.ai_service import AIService
from app.services.license_service import LicenseService
from app.services.desktop_service import DesktopService

# Import utilities
from app.utils.database import HybridDatabaseManager, init_database
from app.utils.calculators import ProfessionalTradingCalculator
from app.utils.system_info import detect_environment

# Global instances (to be initialized in create_app)
db_manager = None
config_manager = None
mt5_service = None
sync_service = None
ai_service = None
license_service = None
desktop_service = None
socketio = None
login_manager = LoginManager()

class AdvancedLogger:
    """Professional logging system from monolithic script"""
    def __init__(self):
        self.log_messages = []
        self.max_log_messages = 5000

        # Setup file logging
        if not os.path.exists('logs'):
            os.makedirs('logs')

        log_handler = RotatingFileHandler(
            'logs/mt5_journal.log',
            maxBytes=10_000_000,  # 10MB
            backupCount=10
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        log_handler.setFormatter(formatter)

        logger = logging.getLogger("mt5_journal")
        logger.setLevel(logging.INFO)
        logger.addHandler(log_handler)

        self.logger = logger

    def add_log(self, level, message, source="System"):
        """Add log entry with timestamp and source"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            'timestamp': timestamp,
            'level': level.upper(),
            'source': source,
            'message': message
        }

        self.log_messages.append(entry)
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages.pop(0)

        # Log to file
        if level.upper() == 'ERROR':
            self.logger.error(f"[{source}] {message}")
        elif level.upper() == 'WARNING':
            self.logger.warning(f"[{source}] {message}")
        elif level.upper() == 'DEBUG':
            self.logger.debug(f"[{source}] {message}")
        else:
            self.logger.info(f"[{source}] {message}")

        # Emit to connected clients
        try:
            if socketio:
                socketio.emit('log_update', entry, namespace='/realtime')
        except Exception:
            pass

# Global logger instance
advanced_logger = None
add_log = None

def create_app():
    """Application factory pattern - creates and configures the Flask app"""
    global db_manager, config_manager, mt5_service, sync_service, ai_service
    global license_service, desktop_service, socketio, advanced_logger, add_log
    
    # Initialize application
    app = Flask(__name__,
               static_folder='static',
               template_folder='templates',
               static_url_path='/static')

    # Step 1: Configuration
    config_manager = ConfigManager()
    config = config_manager.config
    
    # Set Flask secret key
    app.secret_key = config['web_app'].get('secret_key', 'mt5-journal-pro-secret-2024')
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Step 2: Initialize extensions
    Session(app)
    CSRFProtect(app)
    
    # SocketIO initialization
    socketio = SocketIO(app,
                       cors_allowed_origins="*",
                       ping_interval=25,
                       ping_timeout=60,
                       async_mode='threading')

    # Step 3: Initialize database
    db_manager = HybridDatabaseManager()
    init_database()

    # Step 4: Initialize logger
    advanced_logger = AdvancedLogger()
    add_log = advanced_logger.add_log
    add_log('INFO', 'Professional MT5 Trading Journal Started', 'System')

    # Step 5: Initialize services
    mt5_service = MT5Service(config, add_log)
    sync_service = SyncService(config, db_manager, add_log)
    ai_service = AIService(add_log)
    license_service = LicenseService(add_log)
    desktop_service = DesktopService(config, add_log)

    # Step 6: Setup login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(int(user_id))

    # Step 7: Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.analytics import analytics_bp
    from app.routes.trading import trading_bp
    from app.routes.trade_plan import trade_plan_bp
    from app.routes.license import license_bp
    from app.routes.desktop import desktop_bp
    from app.routes.export import export_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(trade_plan_bp)
    app.register_blueprint(license_bp)
    app.register_blueprint(desktop_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(api_bp)

    # Step 8: Context processors
    @app.context_processor
    def inject_hybrid_data():
        """Inject hybrid-specific data into all templates"""
        environment = detect_environment()
        is_demo_mode = not mt5_service.is_connected()
        
        # Get license information
        license_info = license_service.get_license_info()
        
        return {
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'app_name': 'Professional MT5 Journal',
            'app_version': '2.0.0',
            'mt5_connected': mt5_service.is_connected(),
            'demo_mode': is_demo_mode,
            'environment': environment,
            'is_web': environment == 'postgresql',
            'is_desktop': environment == 'sqlite',
            'db_type': environment,
            'is_postgresql': environment == 'postgresql',
            'is_sqlite': environment == 'sqlite',
            'mt5_available': mt5_service.is_available(),
            'hybrid_mode': True,
            'current_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_year': datetime.now().year,
            'current_month': datetime.now().month,
            'current_month_name': datetime.now().strftime('%B'),
            'license_status': license_info['status'],
            'license_valid': license_info['is_valid'],
            'trial_days_left': license_info['trial_days_left'],
            'license_features': license_info['features'],
            'license_message': license_info['message'],
            'is_premium': license_info['status'] == 'licensed' or license_info['status'] == 'free'
        }

    # Step 9: Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return "Page not found", 404

    @app.errorhandler(500)
    def internal_error(error):
        add_log('ERROR', f'Internal server error: {error}', 'Application')
        return "Internal server error", 500

    # Step 10: Before request handlers
    @app.before_request
    def check_license():
        """Check license status before each request"""
        # Skip license check for certain routes
        exempt_routes = ['static', 'auth.login', 'auth.register', 'auth.logout', 'api.validate_license']
        
        if request.endpoint in exempt_routes:
            return
        
        # Check license status
        is_valid, message = license_service.validate_license()
        
        if not is_valid:
            # Allow access to license management page even if expired
            if request.endpoint not in ['license.management', 'api.license_status', 'api.activate_license']:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'error': 'License required',
                        'message': message,
                        'redirect': url_for('license.management')
                    }), 402  # Payment Required
                else:
                    flash(f'⚠️ {message}. Please activate your license.', 'warning')
                    return redirect(url_for('license.management'))

    # Step 11: SocketIO event handlers
    @socketio.on('connect', namespace='/realtime')
    def on_professional_connect():
        """Professional client connection handler"""
        add_log('INFO', f'Professional client connected: {request.sid}', 'WebSocket')
        emit('connection_status', {
            'status': 'connected',
            'message': 'Connected to Professional MT5 Journal',
            'timestamp': datetime.now().isoformat()
        })

    @socketio.on('disconnect', namespace='/realtime')
    def on_professional_disconnect():
        """Professional client disconnection handler"""
        add_log('INFO', f'Professional client disconnected: {request.sid}', 'WebSocket')

    @socketio.on('subscribe', namespace='/realtime')
    def on_professional_subscribe(data):
        """Professional client subscription handler"""
        channels = data.get('channels', [])
        add_log('INFO', f'Professional client {request.sid} subscribed to: {channels}', 'WebSocket')
        emit('subscribed', {'channels': channels, 'timestamp': datetime.now().isoformat()})

    @socketio.on('force_sync', namespace='/realtime')
    def on_professional_force_sync():
        """Professional manual sync handler"""
        add_log('INFO', f'Professional manual sync requested by: {request.sid}', 'WebSocket')
        success = sync_service.sync_with_mt5(force=True)
        emit('sync_complete', {
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'message': 'Professional sync completed' if success else 'Sync failed'
        })

    # Step 12: Initialize background services
    def initialize_background_services():
        """Initialize background threads and services"""
        try:
            # Start auto-sync thread
            sync_service.start_auto_sync()
            
            # Initial sync
            sync_service.sync_with_mt5()
            
            add_log('INFO', 'Background services initialized', 'System')
        except Exception as e:
            add_log('ERROR', f'Background services initialization failed: {e}', 'System')

    # Initialize background services after app context
    with app.app_context():
        initialize_background_services()

    add_log('INFO', 'Flask application initialization completed', 'System')
    return app

def get_app_components():
    """Provide access to app components for other modules"""
    return {
        'db_manager': db_manager,
        'config_manager': config_manager,
        'mt5_service': mt5_service,
        'sync_service': sync_service,
        'ai_service': ai_service,
        'license_service': license_service,
        'desktop_service': desktop_service,
        'socketio': socketio,
        'logger': advanced_logger
    }

# Export components for easy access
__all__ = ['create_app', 'get_app_components', 'add_log']