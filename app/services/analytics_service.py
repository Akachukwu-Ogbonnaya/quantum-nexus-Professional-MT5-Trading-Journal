import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils import add_log

class ProfessionalStatisticsGenerator:
    @staticmethod
    def generate_trading_statistics(df, period="All Time"):
        if df.empty:
            return create_empty_stats()

        try:
            total_trades = len(df)
            winning_trades = len(df[df['profit'] > 0])
            losing_trades = len(df[df['profit'] < 0])
            break_even_trades = len(df[df['profit'] == 0])

            net_profit = float(df['profit'].sum())
            gross_profit = float(df[df['profit'] > 0]['profit'].sum())
            gross_loss = abs(float(df[df['profit'] < 0]['profit'].sum()))

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

            avg_win = float(df[df['profit'] > 0]['profit'].mean()) if winning_trades > 0 else 0
            avg_loss = float(df[df['profit'] < 0]['profit'].mean()) if losing_trades > 0 else 0
            avg_trade = float(df['profit'].mean()) if total_trades > 0 else 0

            rr_ratios = pd.to_numeric(df['actual_rr'], errors='coerce').dropna()
            avg_rr = float(rr_ratios.mean()) if len(rr_ratios) > 0 else 0
            median_rr = float(rr_ratios.median()) if len(rr_ratios) > 0 else 0

            largest_win = float(df['profit'].max())
            largest_loss = float(df['profit'].min())

            return {
                'period': period,
                'total_trades': int(total_trades),
                'winning_trades': int(winning_trades),
                'losing_trades': int(losing_trades),
                'break_even_trades': int(break_even_trades),
                'net_profit': round(net_profit, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),
                'win_rate': round(win_rate, 2),
                'profit_factor': round(profit_factor, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_trade': round(avg_trade, 2),
                'avg_rr': round(avg_rr, 2),
                'median_rr': round(median_rr, 2),
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2),
            }

        except Exception as e:
            add_log('ERROR', f'Statistics generation error: {e}', 'Statistics')
            return create_empty_stats()

def create_empty_stats():
    return {
        'period': "All Time",
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'break_even_trades': 0,
        'net_profit': 0,
        'gross_profit': 0,
        'gross_loss': 0,
        'win_rate': 0,
        'profit_factor': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'avg_trade': 0,
        'avg_rr': 0,
        'median_rr': 0,
        'largest_win': 0,
        'largest_loss': 0,
    }

# Global instance
stats_generator = ProfessionalStatisticsGenerator()