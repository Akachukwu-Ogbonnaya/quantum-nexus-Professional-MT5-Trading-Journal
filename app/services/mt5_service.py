# /app/app/services/mt5_service.py - FIXED VERSION

# FIXED IMPORTS - Changed from 'utils.' to 'app.utils.'
from app.utils.config import config
from app.utils.database import db_manager, get_db_connection

# Rest of your imports...
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os

class MT5Service:
    """Service for MT5 connection and operations"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.symbols_info = {}
        
    def connect(self, account=None, password=None, server=None):
        """Connect to MT5 with provided credentials or from config"""
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
        """Get account information"""
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
                    'server': account_info.server
                }
            return None
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
            return None
    
    def get_positions(self, symbol=None):
        """Get open positions"""
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
        """Get pending orders"""
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
        """Get trade history"""
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
    
    def _parse_position(self, position):
        """Parse MT5 position to dictionary"""
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
    
    def _parse_order(self, order):
        """Parse MT5 order to dictionary"""
        return {
            'ticket': order.ticket,
            'symbol': order.symbol,
            'type': self._get_order_type(order.type),
            'volume': order.volume_current,
            'price': order.price_open,
            'sl': order.sl,
            'tp': order.tp,
            'time': datetime.fromtimestamp(order.time_setup),
            'time_expiration': datetime.fromtimestamp(order.time_expiration) if order.time_expiration else None,
            'magic': order.magic,
            'comment': order.comment
        }
    
    def _parse_deal(self, deal):
        """Parse MT5 deal to dictionary"""
        return {
            'ticket': deal.ticket,
            'order': deal.order,
            'symbol': deal.symbol,
            'type': self._get_deal_type(deal.type),
            'volume': deal.volume,
            'price': deal.price,
            'profit': deal.profit,
            'swap': deal.swap,
            'commission': deal.commission,
            'time': datetime.fromtimestamp(deal.time),
            'magic': deal.magic,
            'comment': deal.comment
        }
    
    def _get_order_type(self, order_type):
        """Convert MT5 order type to string"""
        type_map = {
            mt5.ORDER_TYPE_BUY: 'BUY',
            mt5.ORDER_TYPE_SELL: 'SELL',
            mt5.ORDER_TYPE_BUY_LIMIT: 'BUY_LIMIT',
            mt5.ORDER_TYPE_SELL_LIMIT: 'SELL_LIMIT',
            mt5.ORDER_TYPE_BUY_STOP: 'BUY_STOP',
            mt5.ORDER_TYPE_SELL_STOP: 'SELL_STOP'
        }
        return type_map.get(order_type, 'UNKNOWN')
    
    def _get_deal_type(self, deal_type):
        """Convert MT5 deal type to string"""
        type_map = {
            mt5.DEAL_TYPE_BUY: 'BUY',
            mt5.DEAL_TYPE_SELL: 'SELL',
            mt5.DEAL_TYPE_BALANCE: 'BALANCE',
            mt5.DEAL_TYPE_CREDIT: 'CREDIT',
            mt5.DEAL_TYPE_CHARGE: 'CHARGE',
            mt5.DEAL_TYPE_CORRECTION: 'CORRECTION',
            mt5.DEAL_TYPE_BONUS: 'BONUS',
            mt5.DEAL_TYPE_COMMISSION: 'COMMISSION',
            mt5.DEAL_TYPE_COMMISSION_DAILY: 'COMMISSION_DAILY',
            mt5.DEAL_TYPE_COMMISSION_MONTHLY: 'COMMISSION_MONTHLY',
            mt5.DEAL_TYPE_COMMISSION_AGENT_DAILY: 'COMMISSION_AGENT_DAILY',
            mt5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY: 'COMMISSION_AGENT_MONTHLY',
            mt5.DEAL_TYPE_INTEREST: 'INTEREST',
            mt5.DEAL_TYPE_BUY_CANCELED: 'BUY_CANCELED',
            mt5.DEAL_TYPE_SELL_CANCELED: 'SELL_CANCELED'
        }
        return type_map.get(deal_type, 'UNKNOWN')

# Create global instance
mt5_service = MT5Service()
