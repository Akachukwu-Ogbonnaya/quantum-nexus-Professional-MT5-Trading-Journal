# models/trade.py
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.utils.database import get_db_connection
from app.utils.calculators import (
    safe_float_conversion, 
    calculate_trade_duration, 
    calculate_risk_reward,
    ProfessionalTradingCalculator
)

class Trade:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.ticket_id = kwargs.get('ticket_id')
        self.symbol = kwargs.get('symbol')
        self.type = kwargs.get('type')
        self.volume = safe_float_conversion(kwargs.get('volume'))
        self.entry_price = safe_float_conversion(kwargs.get('entry_price'))
        self.current_price = safe_float_conversion(kwargs.get('current_price'))
        self.exit_price = safe_float_conversion(kwargs.get('exit_price'))
        self.sl_price = safe_float_conversion(kwargs.get('sl_price'))
        self.tp_price = safe_float_conversion(kwargs.get('tp_price'))
        self.entry_time = kwargs.get('entry_time')
        self.exit_time = kwargs.get('exit_time')
        self.profit = safe_float_conversion(kwargs.get('profit'))
        self.commission = safe_float_conversion(kwargs.get('commission'))
        self.swap = safe_float_conversion(kwargs.get('swap'))
        self.comment = kwargs.get('comment')
        self.magic_number = kwargs.get('magic_number')
        self.session = kwargs.get('session')
        self.planned_rr = safe_float_conversion(kwargs.get('planned_rr'))
        self.actual_rr = safe_float_conversion(kwargs.get('actual_rr'))
        self.duration = kwargs.get('duration')
        self.account_balance = safe_float_conversion(kwargs.get('account_balance'))
        self.account_equity = safe_float_conversion(kwargs.get('account_equity'))
        self.account_change_percent = safe_float_conversion(kwargs.get('account_change_percent'))
        self.status = kwargs.get('status', 'OPEN')
        self.floating_pnl = safe_float_conversion(kwargs.get('floating_pnl'))
        self.risk_per_trade = safe_float_conversion(kwargs.get('risk_per_trade'))
        self.margin_used = safe_float_conversion(kwargs.get('margin_used'))
        self.strategy = kwargs.get('strategy')
        self.tags = kwargs.get('tags')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')

    @staticmethod
    def get_all(limit=None, filters=None):
        """Get all trades with optional filtering and limit"""
        conn = get_db_connection()
        try:
            query = 'SELECT * FROM trades WHERE 1=1'
            params = []
            
            if filters:
                if filters.get('symbol'):
                    query += ' AND symbol = ?'
                    params.append(filters['symbol'])
                if filters.get('status'):
                    query += ' AND status = ?'
                    params.append(filters['status'])
                if filters.get('strategy'):
                    query += ' AND strategy = ?'
                    params.append(filters['strategy'])
                if filters.get('session'):
                    query += ' AND session = ?'
                    params.append(filters['session'])
                if filters.get('magic_number'):
                    query += ' AND magic_number = ?'
                    params.append(filters['magic_number'])
            
            query += ' ORDER BY entry_time DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor = conn.cursor()
            if conn.db_type == 'postgresql':
                query = query.replace('?', '%s')
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            trades = []
            for row in rows:
                if conn.db_type == 'postgresql':
                    trade_data = dict(row)
                else:
                    trade_data = dict(zip([col[0] for col in cursor.description], row))
                trades.append(Trade(**trade_data))
            
            return trades
        except Exception as e:
            print(f"Trade.get_all error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_by_ticket(ticket_id):
        """Get trade by ticket ID"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                cursor.execute('SELECT * FROM trades WHERE ticket_id = %s', (ticket_id,))
            else:
                cursor.execute('SELECT * FROM trades WHERE ticket_id = ?', (ticket_id,))
            
            row = cursor.fetchone()
            if row:
                if conn.db_type == 'postgresql':
                    trade_data = dict(row)
                else:
                    trade_data = dict(zip([col[0] for col in cursor.description], row))
                return Trade(**trade_data)
            return None
        except Exception as e:
            print(f"Trade.get_by_ticket error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_open_positions():
        """Get all open positions"""
        return Trade.get_all(filters={'status': 'OPEN'})

    @staticmethod
    def get_closed_trades(limit=None):
        """Get all closed trades"""
        return Trade.get_all(limit=limit, filters={'status': 'CLOSED'})

    @staticmethod
    def get_by_period(period="monthly"):
        """Get trades filtered by time period"""
        conn = get_db_connection()
        try:
            end_date = datetime.now()

            if period == 'daily':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'weekly':
                start_date = end_date - timedelta(days=end_date.weekday())
            elif period == 'monthly':
                start_date = end_date.replace(day=1)
            elif period == '3months':
                start_date = end_date - timedelta(days=90)
            elif period == '6months':
                start_date = end_date - timedelta(days=180)
            elif period == '1year':
                start_date = end_date - timedelta(days=365)
            else:
                # Get all trades
                return Trade.get_all()

            cursor = conn.cursor()
            if conn.db_type == 'postgresql':
                cursor.execute('SELECT * FROM trades WHERE entry_time >= %s', (start_date,))
            else:
                cursor.execute('SELECT * FROM trades WHERE entry_time >= ?', (start_date,))
            
            rows = cursor.fetchall()
            trades = []
            for row in rows:
                if conn.db_type == 'postgresql':
                    trade_data = dict(row)
                else:
                    trade_data = dict(zip([col[0] for col in cursor.description], row))
                trades.append(Trade(**trade_data))
            
            return trades
        except Exception as e:
            print(f"Trade.get_by_period error: {e}")
            return []
        finally:
            conn.close()

    def save(self):
        """Save trade to database (insert or update)"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Calculate additional metrics before saving
            self._calculate_metrics()
            
            values = (
                self.ticket_id,
                self.symbol,
                self.type,
                self.volume,
                self.entry_price,
                self.current_price,
                self.exit_price,
                self.sl_price,
                self.tp_price,
                self.entry_time,
                self.exit_time,
                self.profit,
                self.commission,
                self.swap,
                self.comment,
                self.magic_number,
                self.session,
                self.planned_rr,
                self.actual_rr,
                self.duration,
                self.account_balance,
                self.account_equity,
                self.account_change_percent,
                self.status,
                self.floating_pnl,
                self.risk_per_trade,
                self.margin_used,
                self.strategy,
                self.tags
            )

            if conn.db_type == 'postgresql':
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
            conn.commit()
            
            if not self.id:
                if conn.db_type == 'postgresql':
                    cursor.execute('SELECT id FROM trades WHERE ticket_id = %s', (self.ticket_id,))
                else:
                    cursor.execute('SELECT id FROM trades WHERE ticket_id = ?', (self.ticket_id,))
                result = cursor.fetchone()
                if result:
                    self.id = result[0]
            
            return True
        except Exception as e:
            conn.rollback()
            print(f"Trade.save error: {e}")
            return False
        finally:
            conn.close()

    def _calculate_metrics(self):
        """Calculate trade metrics before saving"""
        try:
            # Risk-reward ratio
            if self.sl_price and self.sl_price > 0:
                self.actual_rr = calculate_risk_reward(
                    self.entry_price,
                    self.exit_price or self.current_price or self.entry_price,
                    self.sl_price,
                    self.type
                )
            else:
                self.actual_rr = None

            # Trade duration
            if self.exit_time:
                self.duration = calculate_trade_duration(self.entry_time, self.exit_time)
            else:
                self.duration = 'Active'

            # Account change percentage
            if self.account_balance and self.account_equity:
                change = ((self.account_equity - self.account_balance) / self.account_balance) * 100
                self.account_change_percent = round(change, 2)
            else:
                self.account_change_percent = 0

            # Risk per trade (simplified)
            if self.account_balance and self.profit:
                self.risk_per_trade = round(abs(self.profit) / self.account_balance * 100, 2)

        except Exception as e:
            print(f"Trade._calculate_metrics error: {e}")

    def update_comment(self, comment):
        """Update trade comment"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                cursor.execute('UPDATE trades SET comment = %s WHERE ticket_id = %s', 
                             (comment, self.ticket_id))
            else:
                cursor.execute('UPDATE trades SET comment = ? WHERE ticket_id = ?', 
                             (comment, self.ticket_id))
            
            conn.commit()
            self.comment = comment
            return True
        except Exception as e:
            conn.rollback()
            print(f"Trade.update_comment error: {e}")
            return False
        finally:
            conn.close()

    def duplicate(self):
        """Duplicate this trade as a new trade"""
        try:
            # Create new trade with current timestamp
            new_trade = Trade(
                ticket_id=f"DUPLICATE_{int(datetime.now().timestamp())}",
                symbol=self.symbol,
                type=self.type,
                volume=self.volume,
                entry_price=self.entry_price,
                sl_price=self.sl_price,
                tp_price=self.tp_price,
                strategy=self.strategy,
                comment=f"Duplicate of {self.ticket_id} - {self.comment}",
                entry_time=datetime.now(),
                status='OPEN'
            )
            
            return new_trade.save()
        except Exception as e:
            print(f"Trade.duplicate error: {e}")
            return False

    def to_dict(self):
        """Convert trade to dictionary"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'symbol': self.symbol,
            'type': self.type,
            'volume': self.volume,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'exit_price': self.exit_price,
            'sl_price': self.sl_price,
            'tp_price': self.tp_price,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'profit': self.profit,
            'commission': self.commission,
            'swap': self.swap,
            'comment': self.comment,
            'magic_number': self.magic_number,
            'session': self.session,
            'planned_rr': self.planned_rr,
            'actual_rr': self.actual_rr,
            'duration': self.duration,
            'account_balance': self.account_balance,
            'account_equity': self.account_equity,
            'account_change_percent': self.account_change_percent,
            'status': self.status,
            'floating_pnl': self.floating_pnl,
            'risk_per_trade': self.risk_per_trade,
            'margin_used': self.margin_used,
            'strategy': self.strategy,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def get_unique_symbols():
        """Get all unique symbols from trades"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT symbol FROM trades ORDER BY symbol')
            rows = cursor.fetchall()
            return [row[0] for row in rows] if rows else []
        except Exception as e:
            print(f"Trade.get_unique_symbols error: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_trades_dataframe(filters=None):
        """Get trades as pandas DataFrame for analysis"""
        trades = Trade.get_all(filters=filters)
        if not trades:
            return pd.DataFrame()
        
        trades_dict = [trade.to_dict() for trade in trades]
        return pd.DataFrame(trades_dict)

    @staticmethod
    def get_performance_summary(period="monthly"):
        """Get performance summary for the specified period"""
        trades = Trade.get_by_period(period)
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'avg_profit': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'profit_factor': 0,
                'avg_rr': 0,
                'expectancy': 0
            }
        
        df = pd.DataFrame([trade.to_dict() for trade in trades])
        closed_trades = df[df['status'] == 'CLOSED']
        
        if len(closed_trades) == 0:
            return {
                'total_trades': len(closed_trades),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'avg_profit': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'profit_factor': 0,
                'avg_rr': 0,
                'expectancy': 0
            }
        
        winning_trades = closed_trades[closed_trades['profit'] > 0]
        losing_trades = closed_trades[closed_trades['profit'] <= 0]
        
        total_profit = closed_trades['profit'].sum()
        gross_profit = winning_trades['profit'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['profit'].sum()) if len(losing_trades) > 0 else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(closed_trades) * 100, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(closed_trades['profit'].mean(), 2),
            'largest_win': round(winning_trades['profit'].max(), 2) if len(winning_trades) > 0 else 0,
            'largest_loss': round(losing_trades['profit'].min(), 2) if len(losing_trades) > 0 else 0,
            'profit_factor': round(profit_factor, 2),
            'avg_rr': round(closed_trades['actual_rr'].mean(), 2) if 'actual_rr' in closed_trades and not closed_trades['actual_rr'].isna().all() else 0,
            'expectancy': round((winning_trades['profit'].mean() * (len(winning_trades)/len(closed_trades)) + 
                               losing_trades['profit'].mean() * (len(losing_trades)/len(closed_trades))), 2)
        }

    @staticmethod
    def get_strategy_performance():
        """Get performance breakdown by strategy"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                cursor.execute('''
                    SELECT 
                        strategy,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losing_trades,
                        AVG(profit) as avg_profit,
                        SUM(profit) as total_profit
                    FROM trades 
                    WHERE status = 'CLOSED' AND strategy IS NOT NULL
                    GROUP BY strategy
                    ORDER BY total_profit DESC
                ''')
            else:
                cursor.execute('''
                    SELECT 
                        strategy,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losing_trades,
                        AVG(profit) as avg_profit,
                        SUM(profit) as total_profit
                    FROM trades 
                    WHERE status = 'CLOSED' AND strategy IS NOT NULL
                    GROUP BY strategy
                    ORDER BY total_profit DESC
                ''')
            
            rows = cursor.fetchall()
            strategies = []
            for row in rows:
                if conn.db_type == 'postgresql':
                    strategy_data = dict(row)
                else:
                    strategy_data = {
                        'strategy': row[0],
                        'total_trades': row[1],
                        'winning_trades': row[2],
                        'losing_trades': row[3],
                        'avg_profit': row[4],
                        'total_profit': row[5]
                    }
                
                if strategy_data['total_trades'] > 0:
                    strategy_data['win_rate'] = round(
                        (strategy_data['winning_trades'] / strategy_data['total_trades']) * 100, 2
                    )
                else:
                    strategy_data['win_rate'] = 0
                
                strategies.append(strategy_data)
            
            return strategies
        except Exception as e:
            print(f"Trade.get_strategy_performance error: {e}")
            return []
        finally:
            conn.close()

    def close_trade(self, exit_price, exit_time=None, commission=0, swap=0):
        """Close the trade with specified parameters"""
        try:
            self.exit_price = safe_float_conversion(exit_price)
            self.exit_time = exit_time or datetime.now()
            self.commission = safe_float_conversion(commission)
            self.swap = safe_float_conversion(swap)
            self.status = 'CLOSED'
            
            # Calculate final profit
            calculator = ProfessionalTradingCalculator()
            self.profit = calculator.calculate_pnl(
                self.symbol,
                self.type,
                self.volume,
                self.entry_price,
                self.exit_price,
                self.commission,
                self.swap
            )
            
            return self.save()
        except Exception as e:
            print(f"Trade.close_trade error: {e}")
            return False

    @staticmethod
    def bulk_update_prices(price_updates):
        """Bulk update current prices for open positions"""
        if not price_updates:
            return True
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            for ticket_id, current_price in price_updates.items():
                if conn.db_type == 'postgresql':
                    cursor.execute(
                        'UPDATE trades SET current_price = %s, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s AND status = %s',
                        (current_price, ticket_id, 'OPEN')
                    )
                else:
                    cursor.execute(
                        'UPDATE trades SET current_price = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ? AND status = ?',
                        (current_price, ticket_id, 'OPEN')
                    )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Trade.bulk_update_prices error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def delete_trade(ticket_id):
        """Delete a trade by ticket ID"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if conn.db_type == 'postgresql':
                cursor.execute('DELETE FROM trades WHERE ticket_id = %s', (ticket_id,))
            else:
                cursor.execute('DELETE FROM trades WHERE ticket_id = ?', (ticket_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Trade.delete_trade error: {e}")
            return False
        finally:
            conn.close()