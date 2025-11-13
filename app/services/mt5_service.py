import os
import time
import threading
import pandas as pd
import numpy as np
from utils.config import config
from utils.database import db_manager, get_db_connection
from utils import add_log
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

# MT5 Import with fallback
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

class UniversalMT5Manager:
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.last_connection = None
        self.connection_attempts = 0
        self.max_attempts = 3

    def initialize_connection(self, account=None, password=None, server=None, terminal_path=None):
        if not MT5_AVAILABLE:
            print("⚠️ MT5 not available - running in demo mode")
            return self.initialize_demo_mode()

        try:
            mt5_config = config.get("mt5", {})
            account = account or mt5_config.get("account", 0)
            password = password or mt5_config.get("password", "")
            server = server or mt5_config.get("server", "")
            terminal_path = terminal_path or mt5_config.get("terminal_path", "")

            if not all([account, password, server]):
                print("❌ MT5 credentials incomplete - please update config.json")
                return self.initialize_demo_mode()

            print(f"🔗 Connecting to MT5: Account={account}, Server={server}")

            if not mt5.initialize(
                path=terminal_path,
                login=int(account),
                password=password,
                server=server
            ):
                error = mt5.last_error()
                print(f"❌ MT5 initialization failed: {error}")
                return self.initialize_demo_mode()

            self.account_info = mt5.account_info()
            if self.account_info:
                self.connected = True
                self.last_connection = datetime.now()
                self.connection_attempts = 0
                return True
            else:
                print("❌ Failed to get account info")
                return self.initialize_demo_mode()

        except Exception as e:
            print(f"❌ MT5 connection error: {e}")
            self.connection_attempts += 1
            return self.initialize_demo_mode()

    def initialize_demo_mode(self):
        print("🔄 Initializing demo mode with sample data")
        self.connected = False
        self.account_info = type('AccountInfo', (), {
            'login': 11146004,
            'balance': 10000.0,
            'equity': 11520.5,
            'margin': 1250.0,
            'margin_free': 10270.5,
            'leverage': 100,
            'currency': 'USD',
            'server': 'Demo-Server'
        })()
        return True

    def reconnect(self):
        if self.connection_attempts >= self.max_attempts:
            print("🔴 Max connection attempts reached - staying in demo mode")
            return False
        print("🔄 Attempting MT5 reconnection...")
        return self.initialize_connection()

    def shutdown(self):
        if MT5_AVAILABLE and self.connected:
            try:
                mt5.shutdown()
                self.connected = False
                print("🔴 MT5 connection closed")
            except Exception as e:
                print(f"⚠️ Error closing MT5 connection: {e}")

class MT5DataSynchronizer:
    def __init__(self):
        self.sync_lock = threading.Lock()
        self.last_sync = None
        sync_config = config.get('sync', {})
        self.sync_interval = sync_config.get('auto_sync_interval', 300)
        self.days_history = sync_config.get('days_history', 90)

    def get_account_data(self):
        if not MT5_AVAILABLE or not mt5_manager.connected:
            return self.get_demo_account_data()

        try:
            account_info = mt5.account_info()
            if account_info:
                return {
                    'balance': float(account_info.balance),
                    'equity': float(account_info.equity),
                    'margin': float(account_info.margin),
                    'free_margin': float(account_info.margin_free),
                    'leverage': int(account_info.leverage),
                    'currency': account_info.currency,
                    'server': account_info.server,
                    'login': account_info.login,
                    'name': getattr(account_info, 'name', 'Unknown'),
                    'company': getattr(account_info, 'company', 'Unknown')
                }
        except Exception as e:
            print(f'Error getting account data: {e}')

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
        if not MT5_AVAILABLE or not mt5_manager.connected:
            return self.get_professional_demo_trades()

        try:
            from_date = datetime.now() - timedelta(days=days_back)
            to_date = datetime.now() + timedelta(days=1)

            deals = mt5.history_deals_get(from_date, to_date) or []
            positions = mt5.positions_get() or []

            trades = {}
            current_account_balance = mt5.account_info().balance if mt5_manager.connected else 10000

            for deal in deals:
                try:
                    if deal.entry in [0, 1]:
                        trade = self.process_professional_deal(deal, current_account_balance)
                        if trade:
                            trades[deal.ticket] = trade
                except Exception as e:
                    print(f'Error processing deal {deal.ticket}: {e}')
                    continue

            for position in positions:
                try:
                    trade = self.process_professional_position(position, current_account_balance)
                    if trade:
                        trades[position.ticket] = trade
                except Exception as e:
                    print(f'Error processing position {position.ticket}: {e}')
                    continue

            trades_list = list(trades.values())
            trades_list.sort(key=lambda x: x.get('entry_time', datetime.min), reverse=True)
            return trades_list

        except Exception as e:
            print(f'Error getting trade history: {e}')
            return self.get_professional_demo_trades()

    def process_professional_deal(self, deal, account_balance):
        try:
            trade_type = self.get_trade_type(deal.type)

            trade = {
                'ticket_id': deal.ticket,
                'symbol': deal.symbol,
                'type': trade_type,
                'volume': deal.volume,
                'entry_price': deal.price,
                'exit_price': deal.price,
                'profit': deal.profit,
                'commission': getattr(deal, 'commission', 0),
                'swap': getattr(deal, 'swap', 0),
                'comment': getattr(deal, 'comment', ''),
                'magic_number': getattr(deal, 'magic', 0),
                'entry_time': datetime.fromtimestamp(deal.time),
                'exit_time': datetime.fromtimestamp(deal.time),
                'status': 'CLOSED',
                'account_balance': account_balance,
                'account_equity': account_balance + deal.profit
            }

            trade = self.calculate_trade_metrics(trade)
            return trade

        except Exception as e:
            print(f'Error processing deal {getattr(deal, "ticket", "unknown")}: {e}')
            return None

    def process_professional_position(self, position, account_balance):
        try:
            trade_type = self.get_trade_type(position.type)
            current_price = getattr(position, 'price_current', position.price_open)
            floating_pnl = position.profit

            trade = {
                'ticket_id': position.ticket,
                'symbol': position.symbol,
                'type': trade_type,
                'volume': position.volume,
                'entry_price': position.price_open,
                'current_price': current_price,
                'sl_price': getattr(position, 'sl', 0),
                'tp_price': getattr(position, 'tp', 0),
                'profit': floating_pnl,
                'commission': 0,
                'swap': 0,
                'comment': getattr(position, 'comment', ''),
                'magic_number': getattr(position, 'magic', 0),
                'entry_time': datetime.fromtimestamp(position.time),
                'status': 'OPEN',
                'floating_pnl': floating_pnl,
                'account_balance': account_balance,
                'account_equity': account_balance + floating_pnl
            }

            trade = self.calculate_trade_metrics(trade)
            return trade

        except Exception as e:
            print(f'Error processing position {getattr(position, "ticket", "unknown")}: {e}')
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
            if trade.get('sl_price') and trade['sl_price'] > 0:
                trade['actual_rr'] = self.calculate_risk_reward(
                    trade['entry_price'],
                    trade.get('exit_price', trade.get('current_price', trade['entry_price'])),
                    trade['sl_price'],
                    trade['type']
                )
            else:
                trade['actual_rr'] = None

            if trade.get('exit_time'):
                trade['duration'] = self.calculate_trade_duration(
                    trade['entry_time'], trade['exit_time']
                )
            else:
                trade['duration'] = 'Active'

            if trade.get('account_balance') and trade.get('account_equity'):
                trade['account_change_percent'] = self.calculate_account_change_percent(
                    trade['account_balance'], trade['account_equity']
                )
            else:
                trade['account_change_percent'] = 0

            if trade.get('account_balance'):
                trade['risk_per_trade'] = round(
                    abs(trade.get('profit', 0)) / trade['account_balance'] * 100, 2
                )
            else:
                trade['risk_per_trade'] = 0

        except Exception as e:
            print(f'Error calculating trade metrics: {e}')

        return trade

    def calculate_risk_reward(self, entry_price, exit_price, sl_price, trade_type):
        entry = self.safe_float_conversion(entry_price)
        exit = self.safe_float_conversion(exit_price)
        sl = self.safe_float_conversion(sl_price)

        if sl == 0 or entry == 0 or entry == sl:
            return None

        try:
            trade_type = str(trade_type).upper().strip()

            if trade_type in ['BUY', 'BUY_LIMIT', 'BUY_STOP']:
                risk = entry - sl
                reward = exit - entry
            elif trade_type in ['SELL', 'SELL_LIMIT', 'SELL_STOP']:
                risk = sl - entry
                reward = entry - exit
            else:
                return None

            if risk != 0:
                rr_ratio = reward / risk
                return round(rr_ratio, 3)

        except Exception as e:
            print(f'Risk-reward calculation error: {e}')
            return None

    def calculate_trade_duration(self, entry_time, exit_time):
        try:
            if isinstance(entry_time, str):
                entry_time = pd.to_datetime(entry_time)
            if isinstance(exit_time, str):
                exit_time = pd.to_datetime(exit_time)

            if not exit_time or pd.isna(exit_time):
                return "Active"

            duration = exit_time - entry_time
            total_seconds = duration.total_seconds()

            if total_seconds < 60:
                return f"{int(total_seconds)}s"
            elif total_seconds < 3600:
                minutes = int(total_seconds / 60)
                seconds = int(total_seconds % 60)
                return f"{minutes}m {seconds}s"
            elif total_seconds < 86400:
                hours = int(total_seconds / 3600)
                minutes = int((total_seconds % 3600) / 60)
                return f"{hours}h {minutes}m"
            else:
                days = int(total_seconds / 86400)
                hours = int((total_seconds % 86400) / 3600)
                return f"{days}d {hours}h"
        except Exception as e:
            print(f'Duration calculation error: {e}')
            return "N/A"

    def calculate_account_change_percent(self, balance, equity):
        try:
            if balance == 0:
                return 0
            return ((equity - balance) / balance) * 100
        except Exception as e:
            print(f'Account change calculation error: {e}')
            return 0

    def safe_float_conversion(self, value, default=0.0):
        if value is None:
            return default

        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = value.replace(',', '').replace('$', '').replace(' ', '').strip()
                if cleaned:
                    return float(cleaned)
            return default
        except (ValueError, TypeError, InvalidOperation):
            return default

    def get_professional_demo_trades(self):
        demo_trades = []
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US30', 'BTCUSD']
        base_time = datetime.now() - timedelta(days=60)
        base_balance = 10000

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

def get_mt5_connection_status():
    try:
        if 'mt5' not in globals():
            try:
                import MetaTrader5 as mt5
                globals()['mt5'] = mt5
            except ImportError:
                print('MT5 module not available - using Demo Mode')
                return False

        if not mt5.initialize():
            print('MT5 initialization failed - using Demo Mode')
            return False

        account_info = mt5.account_info()
        if account_info is None:
            print('No MT5 account info - using Demo Mode')
            return False

        try:
            eurusd_info = mt5.symbol_info("EURUSD")
            if eurusd_info is None:
                print('No market data available - using Demo Mode')
                return False

            tick = mt5.symbol_info_tick("EURUSD")
            if tick is None:
                print('No live tick data - using Demo Mode')
                return False

            tick_time = datetime.fromtimestamp(tick.time)
            time_diff = datetime.now() - tick_time
            if time_diff.total_seconds() > 60:
                print('Stale market data - using Demo Mode')
                return False

        except Exception as e:
            print(f'Market data check failed: {e} - using Demo Mode')
            return False

        print('MT5 Live connection confirmed')
        return True

    except Exception as e:
        print(f'MT5 connection check failed: {e} - using Demo Mode')
        return False

def get_mt5_error_message(error_code):
    error_messages = {
        10013: "Invalid account number",
        10014: "Invalid password", 
        10015: "Invalid server",
        10016: "Invalid terminal path",
        10017: "Trade context is busy",
        10018: "Connection failed",
        10019: "Network error",
        10020: "Timeout error"
    }
    return error_messages.get(error_code, f"MT5 error code: {error_code}")

# Global instances
mt5_manager = UniversalMT5Manager()
mt5_synchronizer = MT5DataSynchronizer()