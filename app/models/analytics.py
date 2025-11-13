# models/analytics.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
from app.utils.database import get_db_connection
from app.utils.calculators import safe_float_conversion, ProfessionalTradingCalculator

class Analytics:
    def __init__(self):
        self.calculator = ProfessionalTradingCalculator()

    @staticmethod
    def generate_trading_statistics(df, period="All Time"):
        """Generate complete trading statistics with period analysis"""
        if df.empty:
            return Analytics.create_empty_stats()

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
            calculator = ProfessionalTradingCalculator()
            consecutive_wins, consecutive_losses = calculator.calculate_consecutive_streaks(df['profit'])
            sharpe_ratio = calculator.calculate_sharpe_ratio(df['profit'])
            recovery_factor = calculator.calculate_recovery_factor(df['profit'])
            expectancy = calculator.calculate_expectancy(win_rate/100, avg_win, avg_loss)
            kelly_criterion = calculator.calculate_kelly_criterion(win_rate/100, avg_win, avg_loss)

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
                'max_drawdown': calculator.calculate_max_drawdown(df['profit'].cumsum().tolist()) if len(df) > 0 else 0.0,
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
            print(f'Statistics generation error: {e}')
            return Analytics.create_empty_stats()

    @staticmethod
    def create_empty_stats():
        """Create empty statistics with all required fields"""
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

    @staticmethod
    def calculate_symbol_performance(df):
        """Calculate symbol performance metrics"""
        if df.empty:
            return []

        symbol_stats = []
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]

            symbol_stats.append({
                'symbol': symbol,
                'trade_count': len(symbol_df),
                'win_rate': len(symbol_df[symbol_df['profit'] > 0]) / len(symbol_df) * 100,
                'net_pnl': symbol_df['profit'].sum(),
                'avg_pnl': symbol_df['profit'].mean(),
                'best_trade': symbol_df['profit'].max(),
                'worst_trade': symbol_df['profit'].min(),
                'total_volume': symbol_df['volume'].sum() if 'volume' in symbol_df.columns else 0
            })

        return sorted(symbol_stats, key=lambda x: x['net_pnl'], reverse=True)

    @staticmethod
    def calculate_strategy_performance(df):
        """Calculate strategy performance metrics"""
        if df.empty or 'strategy' not in df.columns:
            return []

        strategy_stats = []
        for strategy in df['strategy'].unique():
            if pd.isna(strategy) or strategy == '':
                continue

            strategy_df = df[df['strategy'] == strategy]
            winning_trades = len(strategy_df[strategy_df['profit'] > 0])
            total_trades = len(strategy_df)

            strategy_stats.append({
                'name': strategy,
                'trade_count': total_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'net_pnl': strategy_df['profit'].sum(),
                'profit_factor': (strategy_df[strategy_df['profit'] > 0]['profit'].sum() /
                                  abs(strategy_df[strategy_df['profit'] < 0]['profit'].sum()))
                if len(strategy_df[strategy_df['profit'] < 0]) > 0 else float('inf'),
                'avg_rr': strategy_df['actual_rr'].mean() if 'actual_rr' in strategy_df.columns else 0
            })

        return sorted(strategy_stats, key=lambda x: x['net_pnl'], reverse=True)

    @staticmethod
    def calculate_comprehensive_risk_metrics(df):
        """Calculate comprehensive risk metrics from trades data"""
        if df.empty:
            return {
                'overall_score': 0,
                'risk_level': 'Low',
                'max_drawdown': 0,
                'volatility_score': 0,
                'recovery_factor': 0,
                'sharpe_ratio': 0,
                'var_95': 0,
                'expected_shortfall': 0
            }

        try:
            # Calculate basic risk metrics
            profits = df['profit'].tolist()
            equity_curve = np.cumsum(profits)

            # Max Drawdown
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (peak - equity_curve) / peak * 100
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

            # Volatility (standard deviation of returns)
            daily_returns = np.diff(equity_curve) / equity_curve[:-1] * 100 if len(equity_curve) > 1 else [0]
            volatility = np.std(daily_returns) if len(daily_returns) > 0 else 0

            # Sharpe Ratio (simplified)
            sharpe_ratio = np.mean(daily_returns) / volatility if volatility > 0 else 0

            # Value at Risk (95%)
            var_95 = np.percentile(profits, 5) if len(profits) > 0 else 0

            # Expected Shortfall
            losses = [p for p in profits if p < var_95]
            expected_shortfall = np.mean(losses) if losses else var_95

            # Recovery Factor
            net_profit = equity_curve[-1] if len(equity_curve) > 0 else 0
            recovery_factor = net_profit / max_drawdown if max_drawdown > 0 else float('inf')

            # Overall Risk Score (0-100)
            volatility_score = min(100, volatility * 2)
            drawdown_score = min(100, max_drawdown * 3)
            var_score = min(100, abs(var_95) * 10)

            overall_score = (volatility_score + drawdown_score + var_score) / 3

            # Risk Level
            if overall_score < 25:
                risk_level = "Low"
            elif overall_score < 50:
                risk_level = "Moderate"
            elif overall_score < 75:
                risk_level = "High"
            else:
                risk_level = "Extreme"

            return {
                'overall_score': round(overall_score, 1),
                'risk_level': risk_level,
                'max_drawdown': round(max_drawdown, 2),
                'volatility_score': round(volatility_score, 1),
                'recovery_factor': round(recovery_factor, 2),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'var_95': round(var_95, 2),
                'expected_shortfall': round(expected_shortfall, 2)
            }

        except Exception as e:
            print(f'Risk metrics calculation error: {e}')
            return {
                'overall_score': 0,
                'risk_level': 'Unknown',
                'max_drawdown': 0,
                'volatility_score': 0,
                'recovery_factor': 0,
                'sharpe_ratio': 0,
                'var_95': 0,
                'expected_shortfall': 0
            }

    @staticmethod
    def generate_risk_recommendations(risk_metrics):
        """Generate risk management recommendations"""
        recommendations = []

        if risk_metrics['overall_score'] > 70:
            recommendations.extend([
                {
                    'category': 'Position Sizing',
                    'message': 'Reduce position sizes by 50% immediately due to extreme risk exposure',
                    'priority': 'high'
                },
                {
                    'category': 'Risk Management',
                    'message': 'Implement maximum daily loss limit of 2% of account balance',
                    'priority': 'high'
                }
            ])
        elif risk_metrics['overall_score'] > 40:
            recommendations.extend([
                {
                    'category': 'Risk Control',
                    'message': 'Consider reducing position sizes by 25% to manage volatility',
                    'priority': 'medium'
                },
                {
                    'category': 'Diversification',
                    'message': 'Diversify across more symbols to reduce concentration risk',
                    'priority': 'medium'
                }
            ])
        else:
            recommendations.append({
                'category': 'Maintenance',
                'message': 'Current risk levels are well-managed. Maintain current risk parameters',
                'priority': 'low'
            })

        # Drawdown specific recommendations
        if risk_metrics['max_drawdown'] > 20:
            recommendations.append({
                'category': 'Drawdown Control',
                'message': f'Current max drawdown of {risk_metrics["max_drawdown"]}% is concerning. Implement stricter stop-losses',
                'priority': 'high'
            })

        # Volatility recommendations
        if risk_metrics['volatility_score'] > 60:
            recommendations.append({
                'category': 'Volatility Management',
                'message': 'High volatility detected. Consider smoothing trading frequency',
                'priority': 'medium'
            })

        return recommendations

    @staticmethod
    def generate_detailed_risk_metrics(df, risk_metrics):
        """Generate detailed risk metrics table data"""
        if df.empty:
            return []

        try:
            profits = df['profit'].tolist()
            volumes = df['volume'].tolist() if 'volume' in df.columns else [0.1] * len(profits)

            # Calculate additional metrics
            avg_trade_risk = np.mean([abs(p) for p in profits]) if profits else 0
            win_rate = len([p for p in profits if p > 0]) / len(profits) * 100 if profits else 0
            profit_factor = sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0])) if any(
                p < 0 for p in profits) else float('inf')

            # Kelly Criterion
            avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
            avg_loss = np.mean([p for p in profits if p < 0]) if any(p < 0 for p in profits) else 0
            kelly = (win_rate / 100 - (1 - win_rate / 100)) / (avg_win / abs(avg_loss)) if avg_loss != 0 else 0

            detailed_metrics = [
                {
                    'name': 'Max Drawdown',
                    'value': f"{risk_metrics['max_drawdown']}%",
                    'benchmark': '< 10%',
                    'status': 'Excellent' if risk_metrics['max_drawdown'] < 10 else 'Good' if risk_metrics[
                                                                                                  'max_drawdown'] < 20 else 'Poor',
                    'description': 'Maximum peak-to-trough decline in equity'
                },
                {
                    'name': 'Sharpe Ratio',
                    'value': f"{risk_metrics['sharpe_ratio']}",
                    'benchmark': '> 1.0',
                    'status': 'Excellent' if risk_metrics['sharpe_ratio'] > 1.5 else 'Good' if risk_metrics[
                                                                                                   'sharpe_ratio'] > 1.0 else 'Poor',
                    'description': 'Risk-adjusted return metric'
                },
                {
                    'name': 'VaR (95%)',
                    'value': f"${risk_metrics['var_95']:.2f}",
                    'benchmark': '> -2% of equity',
                    'status': 'Excellent' if risk_metrics['var_95'] > -20 else 'Good' if risk_metrics[
                                                                                             'var_95'] > -50 else 'Poor',
                    'description': 'Maximum expected loss at 95% confidence'
                },
                {
                    'name': 'Recovery Factor',
                    'value': f"{risk_metrics['recovery_factor']:.2f}",
                    'benchmark': '> 1.0',
                    'status': 'Excellent' if risk_metrics['recovery_factor'] > 2.0 else 'Good' if risk_metrics[
                                                                                                      'recovery_factor'] > 1.0 else 'Poor',
                    'description': 'Net profit divided by max drawdown'
                },
                {
                    'name': 'Kelly Criterion',
                    'value': f"{kelly:.1%}",
                    'benchmark': '< 25%',
                    'status': 'Excellent' if kelly < 0.1 else 'Good' if kelly < 0.25 else 'Poor',
                    'description': 'Optimal position sizing percentage'
                }
            ]

            return detailed_metrics

        except Exception as e:
            print(f'Detailed risk metrics error: {e}')
            return []

    @staticmethod
    def generate_risk_distribution_chart_data(df):
        """Generate risk distribution chart data"""
        if df.empty:
            return {'labels': [], 'risk_values': []}

        try:
            # Sample last 20 trades for the chart
            sample_trades = df.head(20)
            labels = [f"Trade {i + 1}" for i in range(len(sample_trades))]

            # Calculate risk per trade (simplified as % of profit/volume)
            risk_values = []
            for _, trade in sample_trades.iterrows():
                profit = trade.get('profit', 0)
                volume = trade.get('volume', 0.1)
                risk = abs(profit) / (volume * 1000) * 100 if volume > 0 else 0
                risk_values.append(min(risk, 10))  # Cap at 10% for visualization

            return {
                'labels': labels,
                'risk_values': risk_values
            }

        except Exception as e:
            print(f'Risk distribution chart error: {e}')
            return {'labels': [], 'risk_values': []}

    @staticmethod
    def generate_drawdown_chart_data(df):
        """Generate drawdown analysis chart data"""
        if df.empty:
            return {'dates': [], 'drawdowns': []}

        try:
            profits = df['profit'].tolist()
            equity_curve = np.cumsum(profits)

            # Calculate running drawdown
            peak = np.maximum.accumulate(equity_curve)
            drawdowns = ((peak - equity_curve) / peak * 100).tolist()

            # Sample points for chart (max 50 points)
            if len(drawdowns) > 50:
                step = len(drawdowns) // 50
                drawdowns = drawdowns[::step]
                dates = [f"Point {i + 1}" for i in range(len(drawdowns))]
            else:
                dates = [f"Trade {i + 1}" for i in range(len(drawdowns))]

            return {
                'dates': dates,
                'drawdowns': [round(d, 2) for d in drawdowns]
            }

        except Exception as e:
            print(f'Drawdown chart error: {e}')
            return {'dates': [], 'drawdowns': []}

    @staticmethod
    def generate_risk_concentration_data(df):
        """Generate risk concentration chart data"""
        if df.empty:
            return {'labels': [], 'values': []}

        try:
            # Simplified risk concentration analysis
            symbol_risk = 40  # Example value - would calculate from actual data
            strategy_risk = 35
            time_risk = 25

            return {
                'labels': ['Symbol Concentration', 'Strategy Risk', 'Time-based Risk'],
                'values': [symbol_risk, strategy_risk, time_risk]
            }

        except Exception as e:
            print(f'Risk concentration error: {e}')
            return {'labels': [], 'values': []}

    @staticmethod
    def calculate_trend_metrics(df):
        """Calculate comprehensive trend metrics"""
        if df.empty:
            return {
                'equity_trend': 0,
                'equity_trend_strength': 'Unknown',
                'consistency_score': 0,
                'current_streak': 0,
                'streak_trend': 'Unknown',
                'momentum_score': 0
            }

        try:
            profits = df['profit'].tolist()
            equity_curve = np.cumsum(profits)

            # Equity trend calculation
            if len(equity_curve) > 1:
                start_equity = equity_curve[0]
                end_equity = equity_curve[-1]
                equity_trend = ((end_equity - start_equity) / abs(start_equity)) * 100 if start_equity != 0 else 0
            else:
                equity_trend = 0

            # Trend strength (using linear regression)
            if len(equity_curve) > 2:
                x = np.arange(len(equity_curve))
                slope, intercept = np.polyfit(x, equity_curve, 1)
                trend_strength = abs(slope) / (np.std(equity_curve) + 1e-10) * 100
            else:
                trend_strength = 0

            # Consistency score (based on profit consistency)
            positive_months = len([p for p in profits if p > 0])
            consistency_score = (positive_months / len(profits)) * 100 if profits else 0

            # Current streak
            current_streak = 0
            if profits:
                current_profit = profits[-1]
                for profit in reversed(profits):
                    if (current_profit > 0 and profit > 0) or (current_profit <= 0 and profit <= 0):
                        current_streak += 1 if current_profit > 0 else -1
                    else:
                        break

            # Momentum score (recent performance vs historical)
            if len(profits) > 5:
                recent = profits[-5:]
                historical = profits[:-5]
                recent_avg = np.mean(recent) if recent else 0
                historical_avg = np.mean(historical) if historical else 0
                momentum_score = min(100, max(0, (recent_avg - historical_avg) / (abs(historical_avg) + 1e-10) * 50 + 50))
            else:
                momentum_score = 50

            # Trend strength classification
            if trend_strength > 5:
                trend_strength_text = "Strong"
            elif trend_strength > 2:
                trend_strength_text = "Moderate"
            else:
                trend_strength_text = "Weak"

            # Streak trend classification
            if abs(current_streak) > 3:
                streak_trend = "Significant"
            elif abs(current_streak) > 1:
                streak_trend = "Moderate"
            else:
                streak_trend = "Minor"

            return {
                'equity_trend': round(equity_trend, 2),
                'equity_trend_strength': trend_strength_text,
                'consistency_score': round(consistency_score, 1),
                'current_streak': current_streak,
                'streak_trend': streak_trend,
                'momentum_score': round(momentum_score, 1)
            }

        except Exception as e:
            print(f'Trend metrics calculation error: {e}')
            return {
                'equity_trend': 0,
                'equity_trend_strength': 'Unknown',
                'consistency_score': 0,
                'current_streak': 0,
                'streak_trend': 'Unknown',
                'momentum_score': 0
            }

    @staticmethod
    def get_demo_risk_metrics():
        """Return demo risk metrics for testing when real data is unavailable"""
        return {
            'overall_score': 65,
            'max_drawdown': 15.5,
            'sharpe_ratio': 1.2,
            'win_rate': 58.3,
            'profit_factor': 1.8,
            'avg_win_loss_ratio': 1.5,
            'risk_reward_ratio': 1.7,
            'volatility': 12.3,
            'concentration_risk': 45.0,
            'consistency_score': 72.0
        }

    @staticmethod
    def get_demo_trend_metrics():
        """Demo data for trend analysis when real data is unavailable"""
        return {
            'equity_trend': 1.5,
            'performance_trend': 2.1,
            'monthly_trend': 0.8,
            'pattern_strength': 75,
            'trend_consistency': 82,
            'momentum_score': 68,
            'volatility_trend': -0.3,
            'market_direction': 1,
            'trend_duration': 15,
            'prediction_confidence': 78,
            'overall_score': 72,
            'consistency_score': 82
        }