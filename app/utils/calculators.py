# app/utils/calculators.py
import numpy as np
import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta

def safe_float_conversion(value, default=0.0):
    """Safely convert any value to float with comprehensive error handling"""
    if value is None:
        return default

    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.replace(',', '').replace('$', '').replace(' ', '').strip()
            if cleaned:
                return float(cleaned)
        return default
    except (ValueError, TypeError, InvalidOperation):
        return default

def calculate_risk_reward(entry_price, exit_price, sl_price, trade_type):
    """Calculate risk-reward ratio"""
    return ProfessionalTradingCalculator.calculate_risk_reward(entry_price, exit_price, sl_price, trade_type)

def calculate_trade_duration(entry_time, exit_time):
    """Calculate trade duration"""
    return ProfessionalTradingCalculator.calculate_trade_duration(entry_time, exit_time)

class ProfessionalTradingCalculator:
    """Comprehensive professional trading calculations"""

    @staticmethod
    def calculate_risk_reward(entry_price, exit_price, sl_price, trade_type):
        """Advanced risk-reward calculation with validation"""
        entry = safe_float_conversion(entry_price)
        exit = safe_float_conversion(exit_price)
        sl = safe_float_conversion(sl_price)

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
            return None

    @staticmethod
    def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss, symbol=None):
        """Professional position sizing with symbol consideration"""
        try:
            account_balance = safe_float_conversion(account_balance)
            risk_amount = account_balance * (safe_float_conversion(risk_percent) / 100)
            price_diff = abs(safe_float_conversion(entry_price) - safe_float_conversion(stop_loss))

            if price_diff > 0:
                position_size = risk_amount / price_diff

                # Apply reasonable limits
                max_position = account_balance * 0.1  # Max 10% of account per trade
                position_size = min(position_size, max_position)

                return round(position_size, 4)
        except Exception as e:
            return 0

    @staticmethod
    def calculate_trade_duration(entry_time, exit_time):
        """Calculate trade duration with professional formatting"""
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
            return "N/A"

    @staticmethod
    def calculate_pip_value(symbol, volume, account_currency="USD"):
        """Calculate pip value for risk management"""
        # Simplified pip value calculation
        # In production, this would use current prices and proper pip calculations
        try:
            volume = safe_float_conversion(volume)
            if 'JPY' in symbol:
                pip_value = volume * 0.01
            else:
                pip_value = volume * 0.0001
            return round(pip_value, 2)
        except Exception:
            return 0

    @staticmethod
    def calculate_max_drawdown(equity_curve):
        """Calculate maximum drawdown with professional handling"""
        if not equity_curve or len(equity_curve) == 0:
            return 0

        try:
            peak = equity_curve[0]
            max_drawdown = 0

            for value in equity_curve:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            return round(max_drawdown, 2)
        except Exception as e:
            return 0

    @staticmethod
    def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
        """Advanced Sharpe ratio calculation"""
        if len(returns) < 2:
            return 0

        try:
            excess_returns = np.array(returns) - (risk_free_rate / 252)
            if np.std(excess_returns) == 0:
                return 0
            sharpe = (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)
            return round(sharpe, 3)
        except Exception as e:
            return 0

    @staticmethod
    def calculate_recovery_factor(profits):
        """Recovery Factor (Net Profit / Max Drawdown)"""
        if len(profits) == 0:
            return 0

        try:
            cumulative = profits.cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_drawdown = abs(drawdown.min()) if drawdown.min() < 0 else 0.01

            if max_drawdown == 0:
                return float('inf') if cumulative.iloc[-1] > 0 else 0

            recovery = cumulative.iloc[-1] / max_drawdown
            return round(recovery, 2)
        except Exception as e:
            return 0

    @staticmethod
    def calculate_expectancy(win_rate, avg_win, avg_loss):
        """Trading Expectancy with professional validation"""
        try:
            loss_rate = 1 - win_rate
            expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)
            return round(expectancy, 2)
        except Exception as e:
            return 0

    @staticmethod
    def calculate_kelly_criterion(win_rate, avg_win, avg_loss):
        """Kelly Criterion for position sizing"""
        try:
            if avg_loss == 0:
                return 0
            win_ratio = abs(avg_win / avg_loss)
            kelly = win_rate - ((1 - win_rate) / win_ratio)
            return max(0, round(kelly * 100, 2))  # Return as percentage
        except Exception as e:
            return 0

    @staticmethod
    def calculate_consecutive_streaks(profits):
        """Calculate consecutive winning and losing streaks"""
        if len(profits) == 0:
            return 0, 0

        try:
            wins = profits > 0
            losses = profits < 0

            def max_streak(series):
                max_count = current_count = 0
                for val in series:
                    if val:
                        current_count += 1
                        max_count = max(max_count, current_count)
                    else:
                        current_count = 0
                return max_count

            return max_streak(wins), max_streak(losses)
        except Exception as e:
            return 0, 0

    @staticmethod
    def calculate_account_change_percent(balance, equity):
        """Calculate account change percentage"""
        try:
            if balance == 0:
                return 0
            return ((equity - balance) / balance) * 100
        except Exception as e:
            return 0

# Initialize professional calculator
trading_calc = ProfessionalTradingCalculator()

def create_empty_stats():
    """Create empty statistics with all required fields for template"""
    return {
        'max_drawdown': 0.0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'total_trades': 0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'sharpe_ratio': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'largest_win': 0.0,
        'largest_loss': 0.0,
        'current_drawdown': 0.0,
        'expectancy': 0.0,
        'risk_reward_ratio': 0.0,
        'net_profit': 0.0,
        'winning_trades': 0,
        'losing_trades': 0,
        'avg_trade': 0.0,
        'profit_loss_ratio': 0.0,
        'starting_balance': 0.0,
        'today_pnl': 0.0,
        'week_pnl': 0.0,
        'month_pnl': 0.0,
        'quarter_pnl': 0.0,
        'half_year_pnl': 0.0,
        'year_pnl': 0.0,
        'today_change': 0.0,
        'week_change': 0.0,
        'month_change': 0.0,
        'quarter_change': 0.0,
        'half_year_change': 0.0,
        'year_change': 0.0,
        'avg_risk_per_trade': 0.0,
        'break_even_trades': 0,
        'avg_rr': 0.0,
        'median_rr': 0.0,
        'best_trade_pct': 0.0,
        'worst_trade_pct': 0.0,
        'consecutive_wins': 0,
        'consecutive_losses': 0,
        'recovery_factor': 0.0,
        'kelly_criterion': 0.0,
        'avg_position_size': 0.0,
        'total_volume': 0.0,
        'risk_per_trade_avg': 0.0,
        'avg_trade_duration': "N/A",
        'best_symbol': "N/A",
        'worst_symbol': "N/A",
        'total_symbols_traded': 0,
        'period': "All Time"
    }

class ProfessionalStatisticsGenerator:
    """Generate comprehensive professional trading statistics"""

    @staticmethod
    def generate_trading_statistics(df, period="All Time"):
        """Generate complete trading statistics with period analysis"""
        if df.empty:
            return create_empty_stats()

        try:
            # Basic metrics
            total_trades = len(df)
            winning_trades = len(df[df['profit'] > 0])
            losing_trades = len(df[df['profit'] < 0])
            break_even_trades = len(df[df['profit'] == 0])

            # Profit calculations
            net_profit = float(df['profit'].sum())
            gross_profit = float(df[df['profit'] > 0]['profit'].sum())
            gross_loss = abs(float(df[df['profit'] < 0]['profit'].sum()))

            # Rate calculations
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

            # Average calculations
            avg_win = float(df[df['profit'] > 0]['profit'].mean()) if winning_trades > 0 else 0
            avg_loss = float(df[df['profit'] < 0]['profit'].mean()) if losing_trades > 0 else 0
            avg_trade = float(df['profit'].mean()) if total_trades > 0 else 0

            # Risk-Reward calculations
            rr_ratios = pd.to_numeric(df['actual_rr'], errors='coerce').dropna()
            avg_rr = float(rr_ratios.mean()) if len(rr_ratios) > 0 else 0
            median_rr = float(rr_ratios.median()) if len(rr_ratios) > 0 else 0

            # Extreme values
            largest_win = float(df['profit'].max())
            largest_loss = float(df['profit'].min())

            # Advanced metrics
            consecutive_wins, consecutive_losses = ProfessionalTradingCalculator.calculate_consecutive_streaks(df['profit'])
            sharpe_ratio = ProfessionalTradingCalculator.calculate_sharpe_ratio(df['profit'])
            recovery_factor = ProfessionalTradingCalculator.calculate_recovery_factor(df['profit'])
            expectancy = ProfessionalTradingCalculator.calculate_expectancy(win_rate/100, avg_win, avg_loss)
            kelly_criterion = ProfessionalTradingCalculator.calculate_kelly_criterion(win_rate/100, avg_win, avg_loss)

            # Risk management metrics
            avg_position_size = float(df['volume'].mean()) if 'volume' in df.columns else 0
            total_volume = float(df['volume'].sum()) if 'volume' in df.columns else 0

            # Additional analytics
            avg_trade_duration = "N/A"  # Would calculate from duration data
            best_symbol = df.groupby('symbol')['profit'].sum().idxmax() if len(df['symbol'].unique()) > 0 else "N/A"
            worst_symbol = df.groupby('symbol')['profit'].sum().idxmin() if len(df['symbol'].unique()) > 0 else "N/A"

            return {
                'period': period,

                # Basic Metrics
                'total_trades': int(total_trades),
                'winning_trades': int(winning_trades),
                'losing_trades': int(losing_trades),
                'break_even_trades': int(break_even_trades),
                'net_profit': round(net_profit, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),

                # Performance Ratios
                'win_rate': round(win_rate, 2),
                'profit_factor': round(profit_factor, 2),
                'avg_profit': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_trade': round(avg_trade, 2),
                'avg_rr': round(avg_rr, 2),
                'median_rr': round(median_rr, 2),

                # Extreme Values
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2),
                'best_trade_pct': round((largest_win / float(df['account_balance'].iloc[0]) * 100), 2) if len(df) > 0 else 0,
                'worst_trade_pct': round((largest_loss / float(df['account_balance'].iloc[0]) * 100), 2) if len(df) > 0 else 0,

                # Advanced Analytics
                'consecutive_wins': int(consecutive_wins),
                'consecutive_losses': int(consecutive_losses),
                'sharpe_ratio': sharpe_ratio,
                'recovery_factor': recovery_factor,
                'expectancy': expectancy,
                'kelly_criterion': kelly_criterion,

                # Risk Management
                'avg_position_size': round(avg_position_size, 4),
                'total_volume': round(total_volume, 2),
                'risk_per_trade_avg': round(float(df['risk_per_trade'].mean()), 2) if 'risk_per_trade' in df.columns else 0,

                # Additional Insights
                'avg_trade_duration': avg_trade_duration,
                'best_symbol': best_symbol,
                'worst_symbol': worst_symbol,
                'total_symbols_traded': int(len(df['symbol'].unique())) if 'symbol' in df.columns else 0,

                # Template Required Fields
                'max_drawdown': ProfessionalTradingCalculator.calculate_max_drawdown(df['profit'].cumsum().tolist()) if len(df) > 0 else 0.0,
                'current_drawdown': 0.0,
                'risk_reward_ratio': avg_rr,
                'profit_loss_ratio': profit_factor,
                'starting_balance': float(df['account_balance'].iloc[0]) if len(df) > 0 else 0.0,
                'today_pnl': 0.0,
                'week_pnl': 0.0,
                'month_pnl': 0.0,
                'quarter_pnl': 0.0,
                'half_year_pnl': 0.0,
                'year_pnl': 0.0,
                'today_change': 0.0,
                'week_change': 0.0,
                'month_change': 0.0,
                'quarter_change': 0.0,
                'half_year_change': 0.0,
                'year_change': 0.0,
                'avg_risk_per_trade': round(float(df['risk_per_trade'].mean()), 2) if 'risk_per_trade' in df.columns else 0.0
            }

        except Exception as e:
            return create_empty_stats()

    @staticmethod
    def generate_performance_report(df, start_date, end_date):
        """Generate comprehensive performance report for date range"""
        try:
            if df.empty:
                return {}

            filtered_df = df[
                (df['exit_time'] >= start_date) &
                (df['exit_time'] <= end_date)
            ]

            return ProfessionalStatisticsGenerator.generate_trading_statistics(filtered_df, f"{start_date} to {end_date}")
        except Exception as e:
            return {}

# Initialize statistics generator
stats_generator = ProfessionalStatisticsGenerator()