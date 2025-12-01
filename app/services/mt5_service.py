# /app/app/services/mt5_service.py - WITH GRACEFUL MT5 HANDLING

from app.utils.config import config
from app.utils.database import db_manager, get_db_connection
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os

# Try to import MetaTrader5, but handle if it's not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    print("✅ MetaTrader5 package available")
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 package not available. Running in demo mode.")

class MT5Service:
    """Service for MT5 connection and operations with graceful fallback"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.symbols_info = {}
        self.demo_mode = not MT5_AVAILABLE
        
    def connect(self, account=None, password=None, server=None):
        """Connect to MT5 with graceful fallback to demo mode"""
        if self.demo_mode:
            # Demo mode - no actual MT5 connection
            print("🔧 Running in demo mode (no MT5 connection available)")
            self.connected = True
            self.account_info = self._create_demo_account_info()
            return True
        
        try:
            # Use provided credentials or fall back to config
            account = account or config.get('mt5', {}).get('account', 0)
            password = password or config.get('mt5', {}).get('password', '')
            server = server or config.get('mt5', {}).get('server', '')
            
            terminal_path = config.get('mt5', {}).get('terminal_path', '')
            
            if terminal_path and os.path.exists(terminal_path):
                if not mt5.initialize(path=terminal_path):
                    print(f"❌ MT5 initialization failed. Error: {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    print(f"❌ MT5 initialization failed. Error: {mt5.last_error()}")
                    return False
            
            # Login to account
            if account and password and server:
                authorized = mt5.login(account, password=password, server=server)
                if authorized:
                    self.connected = True
                    self.account_info = mt5.account_info()
                    print(f"✅ Connected to MT5 Account: {account}")
                    return True
                else:
                    print(f"❌ MT5 login failed. Error: {mt5.last_error()}")
                    return False
            else:
                print("⚠️  MT5 credentials not configured. Using demo mode.")
                self.connected = True  # Consider connected for demo mode
                return True
                
        except Exception as e:
            print(f"❌ MT5 connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.demo_mode:
            print("🔧 Demo mode - no disconnect needed")
            return True
            
        try:
            mt5.shutdown()
            self.connected = False
            self.account_info = None
            print("✅ Disconnected from MT5")
            return True
        except Exception as e:
            print(f"❌ MT5 disconnect error: {e}")
            return False
    
    def get_account_info(self):
        """Get account information (demo or real)"""
        if self.demo_mode:
            return self._create_demo_account_info()
        
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            account_info = mt5.account_info()
            if account_info:
                return {
                    'login': account_info.login,
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'margin_level': account_info.margin_level,
                    'currency': account_info.currency,
                    'leverage': account_info.leverage,
                    'name': account_info.name,
                    'server': account_info.server,
                    'demo_mode': False
                }
            return None
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
            return self._create_demo_account_info()
    
    def _create_demo_account_info(self):
        """Create demo account information"""
        return {
            'login': 123456,
            'balance': 10000.00,
            'equity': 10500.50,
            'margin': 1250.75,
            'free_margin': 8749.25,
            'margin_level': 840.25,
            'currency': 'USD',
            'leverage': 100,
            'name': 'Demo Account',
            'server': 'MetaQuotes-Demo',
            'demo_mode': True,
            'note': 'Running in demo mode - MT5 not available'
        }
    
    def get_positions(self, symbol=None):
        """Get open positions (demo returns empty list)"""
        if self.demo_mode:
            return []  # No positions in demo mode
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if positions:
                return [self._parse_position(pos) for pos in positions]
            return []
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            return []
    
    def get_orders(self, symbol=None):
        """Get pending orders (demo returns empty list)"""
        if self.demo_mode:
            return []
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            orders = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
            if orders:
                return [self._parse_order(order) for order in orders]
            return []
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
            return []
    
    def get_history(self, days=90):
        """Get trade history (demo returns empty list or sample data)"""
        if self.demo_mode:
            # Return empty list or create sample history for demo
            return self._create_demo_history(days)
        
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            orders = mt5.history_orders_get(from_date, to_date)
            
            history = []
            if deals:
                for deal in deals:
                    history.append(self._parse_deal(deal))
            
            return history
        except Exception as e:
            print(f"❌ Error getting history: {e}")
            return []
    
    def _create_demo_history(self, days=90):
        """Create sample demo history"""
        # Return empty list for now, or create sample trades if needed
        return []
    
    # Keep the rest of your parsing methods (_parse_position, _parse_order, _parse_deal, etc.)
    # These methods should check for demo_mode if they use mt5 constants
    
    def _parse_position(self, position):
        """Parse MT5 position to dictionary"""
        if self.demo_mode:
            return {}
        
        return {
            'ticket': position.ticket,
            'symbol': position.symbol,
            'type': 'BUY' if position.type == mt5.POSITION_TYPE_BUY else 'SELL',
            'volume': position.volume,
            'entry_price': position.price_open,
            'current_price': position.price_current,
            'sl': position.sl,
            'tp': position.tp,
            'profit': position.profit,
            'swap': position.swap,
            'commission': position.commission,
            'time': datetime.fromtimestamp(position.time),
            'time_update': datetime.fromtimestamp(position.time_update),
            'magic': position.magic,
            'comment': position.comment
        }
    
    # ... rest of your existing methods with similar demo_mode checks

# Create global instance
mt5_service = MT5Service()
