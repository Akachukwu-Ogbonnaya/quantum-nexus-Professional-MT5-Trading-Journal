import os
import threading
import time
import pandas as pd
import numpy as np
import sqlite3
from decimal import InvalidOperation
from datetime import datetime, timedelta

# FIXED: Changed all 'utils.' imports to 'app.utils.'
from app.utils.config import config
from app.utils.database import db_manager, get_db_connection
from app.utils import add_log, trading_calc, safe_float_conversion
from app.services.mt5_service import mt5_service, MT5_AVAILABLE

# Note: socketio and calendar_dashboard need to be imported from their modules
# These will be imported when needed or passed as parameters

class ProfessionalDataStore:
    def __init__(self):
        self.data_lock = threading.RLock()
        self.trades = []
        self.account_data = {}
        self.account_history = []
        self.open_positions = []
        self.calculated_stats = {}
        self.equity_curve = []
        self.calendar_data = {}
        self.initial_import_done = False
        self.last_update = None

class ProfessionalDataSynchronizer:
    def __init__(self, socketio=None, calendar_dashboard=None):
        self.socketio = socketio
        self.calendar_dashboard = calendar_dashboard
        self.sync_lock = threading.Lock()
        self.last_sync = None
        sync_config = config.get('sync', {})
        self.sync_interval = sync_config.get('auto_sync_interval', 300)
        self.days_history = sync_config.get('days_history', 90)
        
        # Initialize global data
        self.global_data = ProfessionalDataStore()

    def sync_with_mt5(self, force=False):
        if not self.sync_lock.acquire(blocking=False) and not force:
            return False

        try:
            if self.last_sync and (datetime.now() - self.last_sync).seconds < 30 and not force:
                return True

            add_log('INFO', 'Starting professional MT5 data synchronization...', 'Sync')

            account_data = self.get_account_data()
            if not account_data:
                add_log('WARNING', 'Using demo account data - MT5 not connected', 'Sync')

            trades = self.get_trade_history(self.days_history)

            success = self.update_database_hybrid(trades, account_data)

            if success:
                with self.global_data.data_lock:
                    self.global_data.trades = trades
                    self.global_data.account_data = account_data
                    self.global_data.open_positions = [t for t in trades if t.get('status') == 'OPEN']
                    self.global_data.last_update = datetime.now()
                    self.global_data.initial_import_done = True

                # Update calendar if available
                if self.calendar_dashboard:
                    self.calendar_dashboard.update_daily_calendar()

                self.last_sync = datetime.now()
                add_log('INFO', f'Professional sync completed: {len(trades)} trades', 'Sync')

                # Emit socketio event if available
                if self.socketio:
                    self.socketio.emit('data_updated', {
                        'timestamp': datetime.now().isoformat(),
                        'trades_count': len(trades),
                        'open_positions': len(self.global_data.open_positions)
                    }, namespace='/realtime')

            return success

        except Exception as e:
            add_log('ERROR', f'Professional synchronization error: {e}', 'Sync')
            return False
        finally:
            try:
                self.sync_lock.release()
            except:
                pass

    def get_account_data(self):
        if not MT5_AVAILABLE or not mt5_service.connected:
            return self.get_demo_account_data()

        try:
            # Use the mt5_service instance
            account_info = mt5_service.get_account_info()
            if account_info:
                return {
                    'balance': float(account_info.get('balance', 0)),
                    'equity': float(account_info.get('equity', 0)),
                    'margin': float(account_info.get('margin', 0)),
                    'free_margin': float(account_info.get('free_margin', 0)),
                    'leverage': int(account_info.get('leverage', 100)),
                    'currency': account_info.get('currency', 'USD'),
                    'server': account_info.get('server', 'Unknown'),
                    'login': account_info.get('login', 0),
                    'name': account_info.get('name', 'Unknown'),
                    'company': account_info.get('company', 'Unknown')
                }
        except Exception as e:
            add_log('ERROR', f'Error getting account data: {e}', 'Sync')

        return self.get_demo_account_data()

    def get_demo_account_data(self):
        return {
            'balance': 25470.50,
            'equity': 26890.25,
            'margin': 3250.75,
            'free_margin': 23639.50,
            'leverage': 100,
            'currency': 'USD',
            'server': 'Professional-Demo',
            'login': 11146004,
            'name': 'Demo Trader',
            'company': 'Trading Professional'
        }

    def get_trade_history(self, days_back):
        if not MT5_AVAILABLE or not mt5_service.connected:
            return self.get_professional_demo_trades()

        try:
            # Use mt5_service to get history
            history = mt5_service.get_history(days_back)
            trades = []
            
            # Process history into trades
            for item in history:
                trade = self.process_trade_item(item)
                if trade:
                    trades.append(trade)
            
            trades.sort(key=lambda x: x.get('entry_time', datetime.min), reverse=True)
            return trades

        except Exception as e:
            add_log('ERROR', f'Error getting trade history: {e}', 'Sync')
            return self.get_professional_demo_trades()

    def process_trade_item(self, item):
        """Process a trade item from MT5 service"""
        try:
            trade = {
                'ticket_id': item.get('ticket', 0),
                'symbol': item.get('symbol', ''),
                'type': item.get('type', 'UNKNOWN'),
                'volume': item.get('volume', 0),
                'entry_price': item.get('entry_price', 0),
                'exit_price': item.get('exit_price', 0),
                'current_price': item.get('current_price', 0),
                'profit': item.get('profit', 0),
                'commission': item.get('commission', 0),
                'swap': item.get('swap', 0),
                'comment': item.get('comment', ''),
                'magic_number': item.get('magic', 0),
                'entry_time': item.get('time', datetime.now()),
                'status': 'CLOSED' if item.get('profit') is not None else 'OPEN'
            }
            
            # Calculate additional metrics
            trade = self.calculate_trade_metrics(trade)
            return trade
            
        except Exception as e:
            add_log('ERROR', f'Error processing trade item: {e}', 'Sync')
            return None

    def get_trade_type(self, mt5_type):
        type_map = {
            0: 'BUY',
            1: 'SELL',
            2: 'BUY_LIMIT',
            3: 'SELL_LIMIT',
            4: 'BUY_STOP',
            5: 'SELL_STOP'
        }
        return type_map.get(mt5_type, 'UNKNOWN')

    def calculate_trade_metrics(self, trade):
        try:
            # Calculate risk-reward ratio
            if trade.get('sl_price') and trade['sl_price'] > 0:
                trade['actual_rr'] = trading_calc.calculate_risk_reward(
                    trade['entry_price'],
                    trade.get('exit_price', trade.get('current_price', trade['entry_price'])),
                    trade['sl_price'],
                    trade['type']
                )
            else:
                trade['actual_rr'] = None

            # Calculate duration
            if trade.get('exit_time'):
                trade['duration'] = trading_calc.calculate_trade_duration(
                    trade['entry_time'], trade['exit_time']
                )
            else:
                trade['duration'] = 'Active'

            # Calculate account change percentage
            if trade.get('account_balance') and trade.get('account_equity'):
                trade['account_change_percent'] = trading_calc.calculate_account_change_percent(
                    trade['account_balance'], trade['account_equity']
                )
            else:
                trade['account_change_percent'] = 0

            # Calculate risk per trade
            if trade.get('account_balance'):
                trade['risk_per_trade'] = round(
                    abs(trade.get('profit', 0)) / trade['account_balance'] * 100, 2
                )
            else:
                trade['risk_per_trade'] = 0

        except Exception as e:
            add_log('ERROR', f'Error calculating trade metrics: {e}', 'Sync')

        return trade

    def get_professional_demo_trades(self):
        """Generate professional demo trades"""
        demo_trades = []
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US30', 'BTCUSD']
        base_time = datetime.now() - timedelta(days=60)
        base_balance = 10000

        # Generate closed trades
        for i in range(125):
            symbol = symbols[i % len(symbols)]
            is_win = i % 3 != 0
            profit = np.random.uniform(50, 300) if is_win else np.random.uniform(-150, -30)
            volume = round(np.random.uniform(0.01, 1.0), 3)

            base_balance += profit * 0.1

            trade_type = 'BUY' if i % 2 == 0 else 'SELL'
            entry_time = base_time + timedelta(hours=i*12)
            exit_time = entry_time + timedelta(hours=np.random.randint(2, 72))

            trade = {
                'ticket_id': 500000 + i,
                'symbol': symbol,
                'type': trade_type,
                'volume': volume,
                'entry_price': round(np.random.uniform(1.0, 1.5), 5),
                'exit_price': round(np.random.uniform(1.0, 1.5), 5),
                'sl_price': round(np.random.uniform(0.995, 1.1), 5),
                'tp_price': round(np.random.uniform(1.1, 1.2), 5),
                'profit': round(profit, 2),
                'commission': round(np.random.uniform(2, 8), 2),
                'swap': round(np.random.uniform(-3, 3), 2),
                'comment': f'Professional trade #{i+1}',
                'magic_number': 12345,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'status': 'CLOSED',
                'account_balance': round(base_balance, 2),
                'account_equity': round(base_balance + profit, 2),
                'strategy': ['Breakout', 'Scalping', 'Swing', 'Position'][i % 4],
                'tags': ['High-Probability', 'News', 'Technical'][i % 3]
            }

            trade = self.calculate_trade_metrics(trade)
            demo_trades.append(trade)

        # Generate open positions
        for i in range(8):
            symbol = symbols[i % len(symbols)]
            trade = {
                'ticket_id': 600000 + i,
                'symbol': symbol,
                'type': 'BUY' if i % 2 == 0 else 'SELL',
                'volume': round(np.random.uniform(0.1, 0.5), 2),
                'entry_price': round(np.random.uniform(1.0, 1.5), 5),
                'current_price': round(np.random.uniform(0.98, 1.52), 5),
                'sl_price': round(np.random.uniform(0.995, 1.1), 5),
                'tp_price': round(np.random.uniform(1.1, 1.2), 5),
                'profit': round(np.random.uniform(-50, 100), 2),
                'status': 'OPEN',
                'entry_time': datetime.now() - timedelta(hours=np.random.randint(1, 48)),
                'floating_pnl': round(np.random.uniform(-50, 100), 2),
                'account_balance': round(base_balance, 2),
                'account_equity': round(base_balance + np.random.uniform(-100, 200), 2),
                'strategy': ['Breakout', 'Scalping', 'Swing'][i % 3]
            }
            trade = self.calculate_trade_metrics(trade)
            demo_trades.append(trade)

        return demo_trades

    def update_database_hybrid(self, trades, account_data):
        conn = db_manager.get_connection()
        
        try:
            if conn.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('BEGIN')
            else:
                cursor = conn.cursor()
                cursor.execute('BEGIN TRANSACTION')

            for trade in trades:
                self.insert_or_update_trade_hybrid(cursor, trade, account_data, conn.db_type)

            self.update_account_history_hybrid(cursor, account_data, conn.db_type)

            conn.commit()
            add_log('INFO', f'Hybrid database update: {len(trades)} trades to {conn.db_type}', 'Database')
            return True

        except Exception as e:
            conn.rollback()
            add_log('ERROR', f'Hybrid database update error: {e}', 'Database')
            return False
        finally:
            conn.close()

    def insert_or_update_trade_hybrid(self, cursor, trade, account_data, db_type):
        try:
            values = (
                trade.get('ticket_id'),
                trade.get('symbol'),
                trade.get('type'),
                safe_float_conversion(trade.get('volume')),
                safe_float_conversion(trade.get('entry_price')),
                safe_float_conversion(trade.get('current_price', trade.get('entry_price'))),
                safe_float_conversion(trade.get('exit_price')),
                safe_float_conversion(trade.get('sl_price')),
                safe_float_conversion(trade.get('tp_price')),
                trade.get('entry_time'),
                trade.get('exit_time'),
                safe_float_conversion(trade.get('profit')),
                safe_float_conversion(trade.get('commission')),
                safe_float_conversion(trade.get('swap')),
                trade.get('comment', ''),
                trade.get('magic_number', 0),
                trade.get('session', ''),
                safe_float_conversion(trade.get('planned_rr')),
                safe_float_conversion(trade.get('actual_rr')),
                trade.get('duration', ''),
                safe_float_conversion(trade.get('account_balance', account_data.get('balance', 0))),
                safe_float_conversion(trade.get('account_equity', account_data.get('equity', 0))),
                safe_float_conversion(trade.get('account_change_percent', 0)),
                trade.get('status', 'CLOSED'),
                safe_float_conversion(trade.get('floating_pnl', 0)),
                safe_float_conversion(trade.get('risk_per_trade', 0)),
                safe_float_conversion(trade.get('margin_used', 0)),
                trade.get('strategy', ''),
                trade.get('tags', '')
            )

            if db_type == 'postgresql':
                query = '''
                    INSERT INTO trades (
                        ticket_id, symbol, type, volume, entry_price, current_price, exit_price,
                        sl_price, tp_price, entry_time, exit_time, profit, commission, swap,
                        comment, magic_number, session, planned_rr, actual_rr, duration, 
                        account_balance, account_equity, account_change_percent, status, 
                        floating_pnl, risk_per_trade, margin_used, strategy, tags, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                             %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        type = EXCLUDED.type,
                        volume = EXCLUDED.volume,
                        entry_price = EXCLUDED.entry_price,
                        current_price = EXCLUDED.current_price,
                        exit_price = EXCLUDED.exit_price,
                        sl_price = EXCLUDED.sl_price,
                        tp_price = EXCLUDED.tp_price,
                        entry_time = EXCLUDED.entry_time,
                        exit_time = EXCLUDED.exit_time,
                        profit = EXCLUDED.profit,
                        commission = EXCLUDED.commission,
                        swap = EXCLUDED.swap,
                        comment = EXCLUDED.comment,
                        magic_number = EXCLUDED.magic_number,
                        session = EXCLUDED.session,
                        planned_rr = EXCLUDED.planned_rr,
                        actual_rr = EXCLUDED.actual_rr,
                        duration = EXCLUDED.duration,
                        account_balance = EXCLUDED.account_balance,
                        account_equity = EXCLUDED.account_equity,
                        account_change_percent = EXCLUDED.account_change_percent,
                        status = EXCLUDED.status,
                        floating_pnl = EXCLUDED.floating_pnl,
                        risk_per_trade = EXCLUDED.risk_per_trade,
                        margin_used = EXCLUDED.margin_used,
                        strategy = EXCLUDED.strategy,
                        tags = EXCLUDED.tags,
                        updated_at = CURRENT_TIMESTAMP
                '''
            else:
                query = '''
                    INSERT OR REPLACE INTO trades (
                        ticket_id, symbol, type, volume, entry_price, current_price, exit_price,
                        sl_price, tp_price, entry_time, exit_time, profit, commission, swap,
                        comment, magic_number, session, planned_rr, actual_rr, duration, 
                        account_balance, account_equity, account_change_percent, status, 
                        floating_pnl, risk_per_trade, margin_used, strategy, tags, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                             ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                '''

            cursor.execute(query, values)

        except Exception as e:
            add_log('ERROR', f'Hybrid trade save error {trade.get("ticket_id")}: {e}', 'Database')

    def update_account_history_hybrid(self, cursor, account_data, db_type):
        try:
            values = (
                datetime.now(),
                account_data.get('balance', 0),
                account_data.get('equity', 0),
                account_data.get('margin', 0),
                account_data.get('free_margin', 0),
                account_data.get('leverage', 100),
                account_data.get('currency', 'USD'),
                account_data.get('server', 'MT5')
            )

            if db_type == 'postgresql':
                query = '''
                    INSERT INTO account_history 
                    (timestamp, balance, equity, margin, free_margin, leverage, currency, server)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                '''
            else:
                query = '''
                    INSERT INTO account_history 
                    (timestamp, balance, equity, margin, free_margin, leverage, currency, server)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''

            cursor.execute(query, values)
        except Exception as e:
            add_log('ERROR', f'Hybrid account history update error: {e}', 'Database')

class ProfessionalAutoSyncThread(threading.Thread):
    def __init__(self, data_synchronizer, interval=300):
        super().__init__(daemon=True)
        self.data_synchronizer = data_synchronizer
        self.interval = interval
        self.running = True
        self.last_backup = None

    def run(self):
        add_log('INFO', f'Professional auto-sync started (interval: {self.interval}s)', 'AutoSync')

        while self.running:
            try:
                self.data_synchronizer.sync_with_mt5()

                now = datetime.now()
                if (self.last_backup is None or
                    (now.hour == 2 and now.minute < 5 and
                     (self.last_backup is None or self.last_backup.date() != now.date()))):
                    self.backup_database()
                    self.last_backup = now

            except Exception as e:
                add_log('ERROR', f'Auto-sync error: {e}', 'AutoSync')

            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        self.running = False

    def backup_database(self):
        try:
            if not os.path.exists('database/backups'):
                os.makedirs('database/backups')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'database/backups/backup_{timestamp}.db'
            
            conn = get_db_connection()
            if hasattr(conn, 'backup'):
                backup_conn = sqlite3.connect(backup_file)
                conn.backup(backup_conn)
                backup_conn.close()
            
            conn.close()
            add_log('INFO', f'Database backup created: {backup_file}', 'Backup')
            return True
        except Exception as e:
            add_log('ERROR', f'Backup error: {e}', 'Backup')
            return False

# ============================================================================
# Factory function and SyncService Class
# ============================================================================

def create_sync_service(socketio=None, calendar_dashboard=None):
    """Factory function to create sync service with dependencies"""
    synchronizer = ProfessionalDataSynchronizer(socketio, calendar_dashboard)
    auto_sync_thread = ProfessionalAutoSyncThread(
        synchronizer, 
        interval=config.get('sync', {}).get('auto_sync_interval', 300)
    )
    return synchronizer, auto_sync_thread


class SyncService:
    """
    Main SyncService class that wraps ProfessionalDataSynchronizer for clean imports.
    This provides backward compatibility and a clean interface for the rest of the application.
    """
    
    def __init__(self, socketio=None, calendar_dashboard=None):
        """
        Initialize SyncService with optional dependencies.
        
        Args:
            socketio: SocketIO instance for real-time updates
            calendar_dashboard: Calendar dashboard instance for calendar updates
        """
        self.synchronizer = ProfessionalDataSynchronizer(socketio, calendar_dashboard)
        self.auto_sync_thread = None
        
    def init_app(self, app):
        """
        Initialize with Flask app and start auto-sync thread.
        
        Args:
            app: Flask application instance
        """
        # Store app reference
        self.app = app
        
        # Start auto-sync thread if auto-sync is enabled
        sync_config = config.get('sync', {})
        auto_sync = sync_config.get('auto_sync', True)
        
        if auto_sync:
            self.auto_sync_thread = ProfessionalAutoSyncThread(
                self.synchronizer,
                interval=sync_config.get('auto_sync_interval', 300)
            )
            self.auto_sync_thread.start()
            add_log('Auto-sync thread started', 'INFO', 'SyncService')
        
        add_log('SyncService initialized with Flask app', 'INFO', 'SyncService')
        return self
    
    def sync_trades(self, force=False):
        """
        Sync trades with MT5/database.
        
        Args:
            force: Force sync even if recently synced
            
        Returns:
            dict: Sync result
        """
        result = self.synchronizer.sync_with_mt5(force)
        
        if result:
            trades = self.synchronizer.global_data.trades
            open_positions = self.synchronizer.global_data.open_positions
            
            return {
                'success': True,
                'trades_synced': len(trades),
                'open_positions': len(open_positions),
                'last_update': self.synchronizer.global_data.last_update.isoformat() 
                if self.synchronizer.global_data.last_update else None
            }
        else:
            return {
                'success': False,
                'error': 'Sync failed',
                'trades_synced': 0
            }
    
    def get_trades(self):
        """
        Get all trades from synchronized data.
        
        Returns:
            list: List of trades
        """
        return self.synchronizer.global_data.trades
    
    def get_open_positions(self):
        """
        Get open positions.
        
        Returns:
            list: List of open positions
        """
        return self.synchronizer.global_data.open_positions
    
    def get_account_data(self):
        """
        Get account data.
        
        Returns:
            dict: Account data
        """
        return self.synchronizer.global_data.account_data
    
    def get_calculated_stats(self):
        """
        Get calculated statistics.
        
        Returns:
            dict: Calculated statistics
        """
        # Calculate stats if not already calculated
        if not self.synchronizer.global_data.calculated_stats:
            trades = self.get_trades()
            if trades:
                self.synchronizer.global_data.calculated_stats = trading_calc.calculate_statistics(trades)
        
        return self.synchronizer.global_data.calculated_stats
    
    def get_sync_status(self):
        """
        Get sync service status.
        
        Returns:
            dict: Sync status
        """
        return {
            'initialized': self.synchronizer.global_data.initial_import_done,
            'last_sync': self.synchronizer.last_sync.isoformat() if self.synchronizer.last_sync else None,
            'auto_sync_running': self.auto_sync_thread and self.auto_sync_thread.is_alive() if self.auto_sync_thread else False,
            'total_trades': len(self.synchronizer.global_data.trades),
            'open_positions': len(self.synchronizer.global_data.open_positions),
            'last_update': self.synchronizer.global_data.last_update.isoformat() if self.synchronizer.global_data.last_update else None
        }
    
    def stop_auto_sync(self):
        """
        Stop the auto-sync thread.
        """
        if self.auto_sync_thread:
            self.auto_sync_thread.stop()
            self.auto_sync_thread.join(timeout=5)
            add_log('Auto-sync thread stopped', 'INFO', 'SyncService')
    
    def __getattr__(self, name):
        """
        Delegate unknown methods to the synchronizer.
        
        Args:
            name: Method name
            
        Returns:
            Callable: Method from synchronizer
        """
        # Delegate to synchronizer if method not found in SyncService
        if hasattr(self.synchronizer, name):
            return getattr(self.synchronizer, name)
        raise AttributeError(f"'SyncService' object has no attribute '{name}'")


# Create global instance
_sync_service_instance = None


def get_sync_service(socketio=None, calendar_dashboard=None):
    """
    Get or create the global SyncService instance.
    
    Args:
        socketio: SocketIO instance
        calendar_dashboard: Calendar dashboard instance
        
    Returns:
        SyncService: Global sync service instance
    """
    global _sync_service_instance
    
    if _sync_service_instance is None:
        _sync_service_instance = SyncService(socketio, calendar_dashboard)
    
    return _sync_service_instance


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'ProfessionalDataStore',
    'ProfessionalDataSynchronizer',
    'ProfessionalAutoSyncThread',
    'SyncService',
    'create_sync_service',
    'get_sync_service'
]
