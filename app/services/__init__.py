# app/services/__init__.py
from flask import current_app
import threading
import time
from datetime import datetime, timedelta
import functools

# Import all services
from .mt5_service import MT5Service
from .sync_service import SyncService
from .ai_service import AIService
from .license_service import LicenseService
from .desktop_service import DesktopService

# Export all services for easy access
__all__ = [
    'MT5Service',
    'SyncService', 
    'AIService',
    'LicenseService',
    'DesktopService'
]

# Service manager for coordinating all services
class ServiceManager:
    """Manages initialization and coordination of all services"""
    
    def __init__(self, app):
        self.app = app
        self.services = {}
        self.background_threads = {}
        self.running = False
        
    def initialize_services(self, config, add_log):
        """Initialize all services with app context"""
        try:
            # Initialize MT5 Service
            self.services['mt5'] = MT5Service(config, add_log)
            
            # Initialize Sync Service (depends on MT5)
            self.services['sync'] = SyncService(
                config, 
                self.services['mt5'],
                add_log
            )
            
            # Initialize AI Service
            self.services['ai'] = AIService(add_log)
            
            # Initialize License Service
            self.services['license'] = LicenseService(add_log)
            
            # Initialize Desktop Service
            self.services['desktop'] = DesktopService(config, add_log)
            
            # Start background services
            self.start_background_services()
            
            add_log('INFO', 'All services initialized successfully', 'ServiceManager')
            
        except Exception as e:
            add_log('ERROR', f'Service initialization failed: {e}', 'ServiceManager')
            raise
    
    def start_background_services(self):
        """Start all background services and threads"""
        self.running = True
        
        # Start auto-sync thread
        sync_thread = threading.Thread(
            target=self._auto_sync_worker,
            daemon=True,
            name="AutoSyncThread"
        )
        sync_thread.start()
        self.background_threads['auto_sync'] = sync_thread
        
        # Start license validation thread
        license_thread = threading.Thread(
            target=self._license_validation_worker, 
            daemon=True,
            name="LicenseValidationThread"
        )
        license_thread.start()
        self.background_threads['license_validation'] = license_thread
        
        # Start desktop monitoring thread (if in desktop mode)
        if self.services['desktop'].is_desktop_environment():
            desktop_thread = threading.Thread(
                target=self._desktop_monitoring_worker,
                daemon=True,
                name="DesktopMonitoringThread"
            )
            desktop_thread.start()
            self.background_threads['desktop_monitoring'] = desktop_thread
    
    def stop_background_services(self):
        """Stop all background services"""
        self.running = False
        
        # Wait for threads to terminate
        for thread_name, thread in self.background_threads.items():
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        current_app.logger.add_log('INFO', 'Background services stopped', 'ServiceManager')
    
    def _auto_sync_worker(self):
        """Background worker for automatic synchronization"""
        sync_interval = self.services['sync'].get_sync_interval()
        last_sync = None
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if it's time to sync
                should_sync = (
                    last_sync is None or
                    (current_time - last_sync).total_seconds() >= sync_interval or
                    current_time.hour == 2 and current_time.minute < 5  # Daily at 2 AM
                )
                
                if should_sync:
                    success = self.services['sync'].sync_with_mt5()
                    if success:
                        last_sync = current_time
                    
                    # Emit real-time update
                    if hasattr(current_app, 'socketio'):
                        current_app.socketio.emit('sync_status', {
                            'last_sync': last_sync.isoformat() if last_sync else None,
                            'success': success,
                            'timestamp': current_time.isoformat()
                        }, namespace='/realtime')
                
                # Sleep with interruption check
                for _ in range(sync_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                current_app.logger.add_log('ERROR', f'Auto-sync worker error: {e}', 'ServiceManager')
                time.sleep(60)  # Wait before retrying
    
    def _license_validation_worker(self):
        """Background worker for license validation"""
        while self.running:
            try:
                # Validate license every hour
                is_valid, message = self.services['license'].validate_license()
                
                # Emit license status update
                if hasattr(current_app, 'socketio'):
                    current_app.socketio.emit('license_status', {
                        'is_valid': is_valid,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    }, namespace='/realtime')
                
                # Sleep for 1 hour
                for _ in range(3600):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                current_app.logger.add_log('ERROR', f'License validation worker error: {e}', 'ServiceManager')
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _desktop_monitoring_worker(self):
        """Background worker for desktop-specific monitoring"""
        while self.running:
            try:
                # Monitor desktop-specific resources
                self.services['desktop'].monitor_system_resources()
                
                # Check for updates
                self.services['desktop'].check_for_updates()
                
                # Sleep for 5 minutes
                for _ in range(300):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                current_app.logger.add_log('ERROR', f'Desktop monitoring worker error: {e}', 'ServiceManager')
                time.sleep(60)  # Wait 1 minute before retrying
    
    def get_service(self, service_name):
        """Get a specific service by name"""
        return self.services.get(service_name)
    
    def get_all_services(self):
        """Get all services"""
        return self.services.copy()

# Service decorators and utilities
def with_services(service_names):
    """Decorator to inject specific services into function"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get service manager from app context
            service_manager = current_app.service_manager
            
            # Inject requested services
            services_to_inject = {}
            for name in service_names:
                services_to_inject[name] = service_manager.get_service(name)
            
            return func(services=services_to_inject, *args, **kwargs)
        return wrapper
    return decorator

def service_required(service_name):
    """Decorator to ensure a service is available"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            service_manager = current_app.service_manager
            service = service_manager.get_service(service_name)
            
            if not service or not service.is_available():
                raise ServiceUnavailableError(f"Service {service_name} is not available")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class ServiceUnavailableError(Exception):
    """Exception raised when a required service is unavailable"""
    pass

# Service factory for creating service instances
class ServiceFactory:
    """Factory for creating service instances with proper dependencies"""
    
    @staticmethod
    def create_mt5_service(config, add_log):
        """Create MT5 service instance"""
        return MT5Service(config, add_log)
    
    @staticmethod
    def create_sync_service(config, mt5_service, add_log):
        """Create sync service instance"""
        return SyncService(config, mt5_service, add_log)
    
    @staticmethod
    def create_ai_service(add_log):
        """Create AI service instance"""
        return AIService(add_log)
    
    @staticmethod
    def create_license_service(add_log):
        """Create license service instance"""
        return LicenseService(add_log)
    
    @staticmethod
    def create_desktop_service(config, add_log):
        """Create desktop service instance"""
        return DesktopService(config, add_log)

# Service status monitoring
class ServiceMonitor:
    """Monitors health and status of all services"""
    
    def __init__(self):
        self.service_status = {}
        self.last_check = {}
    
    def check_service_health(self, service_name, service_instance):
        """Check health of a specific service"""
        try:
            status = {
                'name': service_name,
                'available': service_instance.is_available(),
                'last_checked': datetime.now().isoformat(),
                'status': 'healthy'
            }
            
            # Service-specific health checks
            if service_name == 'mt5':
                status['connected'] = service_instance.is_connected()
                status['demo_mode'] = not service_instance.is_connected()
            
            elif service_name == 'sync':
                status['last_sync'] = service_instance.get_last_sync()
                status['sync_interval'] = service_instance.get_sync_interval()
            
            elif service_name == 'license':
                is_valid, message = service_instance.validate_license()
                status['valid'] = is_valid
                status['message'] = message
            
            self.service_status[service_name] = status
            self.last_check[service_name] = datetime.now()
            
            return status
            
        except Exception as e:
            current_app.logger.add_log('ERROR', f'Service health check failed for {service_name}: {e}', 'ServiceMonitor')
            return {
                'name': service_name,
                'available': False,
                'status': 'unhealthy',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }
    
    def get_all_service_status(self):
        """Get status of all services"""
        service_manager = current_app.service_manager
        all_services = service_manager.get_all_services()
        
        status_report = {}
        for name, service in all_services.items():
            status_report[name] = self.check_service_health(name, service)
        
        return status_report
    
    def is_system_healthy(self):
        """Check if all critical services are healthy"""
        status_report = self.get_all_service_status()
        
        critical_services = ['mt5', 'sync', 'license']
        for service_name in critical_services:
            status = status_report.get(service_name, {})
            if not status.get('available', False):
                return False
        
        return True

# Service initialization function
def init_services(app, config, add_log):
    """Initialize all services with the application"""
    
    # Create service manager
    service_manager = ServiceManager(app)
    app.service_manager = service_manager
    
    # Initialize all services
    service_manager.initialize_services(config, add_log)
    
    # Create service monitor
    app.service_monitor = ServiceMonitor()
    
    # Register service cleanup on app shutdown
    @app.teardown_appcontext
    def shutdown_services(exception=None):
        if exception:
            add_log('ERROR', f'App context teardown with exception: {exception}', 'Services')
        service_manager.stop_background_services()
    
    add_log('INFO', 'Services initialization completed', 'Services')
    return service_manager

# Utility function to get services from any module
def get_service(service_name):
    """Get a service by name from current app context"""
    if hasattr(current_app, 'service_manager'):
        return current_app.service_manager.get_service(service_name)
    return None

def get_all_services():
    """Get all services from current app context"""
    if hasattr(current_app, 'service_manager'):
        return current_app.service_manager.get_all_services()
    return {}

# Export utility classes and functions
__all__.extend([
    'ServiceManager',
    'ServiceFactory', 
    'ServiceMonitor',
    'ServiceUnavailableError',
    'with_services',
    'service_required',
    'init_services',
    'get_service',
    'get_all_services'
])

# Service constants
SYNC_INTERVAL = 300  # 5 minutes
LICENSE_CHECK_INTERVAL = 3600  # 1 hour
DESKTOP_MONITOR_INTERVAL = 300  # 5 minutes

__all__.extend([
    'SYNC_INTERVAL',
    'LICENSE_CHECK_INTERVAL', 
    'DESKTOP_MONITOR_INTERVAL'
])