from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.database import get_db_connection, get_universal_connection, conn_fetch_dataframe
from app.utils.stats import stats_generator, create_empty_stats
from app.utils.calendar import calendar_dashboard
from app.utils.hybrid import hybrid_compatible
from app.utils.risk import (
    calculate_comprehensive_risk_metrics,
    generate_risk_recommendations,
    generate_detailed_risk_metrics,
    generate_risk_distribution_chart_data,
    generate_drawdown_chart_data,
    generate_risk_concentration_data,
    get_demo_risk_metrics,
    get_demo_risk_recommendations,
    get_demo_detailed_risk_metrics,
    get_demo_risk_chart_data,
    get_demo_drawdown_chart_data,
    get_demo_concentration_chart_data
)
from app.utils.trend import (
    calculate_trend_metrics,
    generate_trend_insights,
    generate_equity_trend_data,
    calculate_trend_distribution,
    generate_monthly_trend_data,
    generate_pattern_analysis_data,
    get_demo_trend_metrics
)
from app.utils.mt5 import get_mt5_connection_status
import pandas as pd
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/statistics')
@login_required
@hybrid_compatible
def statistics_dashboard():
    """Main statistics dashboard - HYBRID COMPATIBLE VERSION"""
    period = request.args.get('period', 'monthly')

    conn = get_universal_connection()
    try:
        # Get filtered data using existing functions
        df = get_trades_by_period(conn, period)

        # Use EXISTING stats generator (already in your app.py)
        stats = stats_generator.generate_trading_statistics(df, period.capitalize())

        # Get additional data using existing calendar system
        symbol_stats = calculate_symbol_performance(df)
        strategy_stats = calculate_strategy_performance(df)
        calendar_data = calendar_dashboard.get_monthly_calendar(
            datetime.now().year,
            datetime.now().month
        )

        return render_template('statistics/executive_dashboard.html',
                               stats=stats,
                               symbol_stats=symbol_stats,
                               strategy_stats=strategy_stats,
                               calendar_data=calendar_data,
                               current_period=period)

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Statistics dashboard error: {e}', 'Statistics')
        return render_template('statistics/executive_dashboard.html',
                               stats=create_empty_stats(),
                               symbol_stats=[],
                               strategy_stats=[],
                               calendar_data={},
                               current_period=period)
    finally:
        conn.close()

@analytics_bp.route('/risk_analysis')
@login_required
@hybrid_compatible
def risk_analysis():
    """Comprehensive Risk Analysis Dashboard"""
    period = request.args.get('period', 'monthly')

    # AUTO-DETECTION: This will now switch automatically
    is_demo_mode = not get_mt5_connection_status()

    try:
        conn = get_db_connection()
        df = get_trades_by_period(conn, period)

        if df.empty:
            # Return DEMO data structure if no data (NOT empty)
            return render_template('statistics/risk_analysis.html',
                                   risk_metrics=get_demo_risk_metrics(),
                                   risk_recommendations=get_demo_risk_recommendations(),
                                   detailed_metrics=get_demo_detailed_risk_metrics(),
                                   risk_chart_data=get_demo_risk_chart_data(),
                                   drawdown_chart_data=get_demo_drawdown_chart_data(),
                                   concentration_chart_data=get_demo_concentration_chart_data(),
                                   current_period=period,
                                   is_demo_mode=is_demo_mode,
                                   auto_refresh=True)

        # Calculate comprehensive risk metrics
        risk_metrics = calculate_comprehensive_risk_metrics(df)
        risk_recommendations = generate_risk_recommendations(risk_metrics)
        detailed_metrics = generate_detailed_risk_metrics(df, risk_metrics)

        # Generate chart data
        risk_chart_data = generate_risk_distribution_chart_data(df)
        drawdown_chart_data = generate_drawdown_chart_data(df)
        concentration_chart_data = generate_risk_concentration_data(df)

        return render_template('statistics/risk_analysis.html',
                               risk_metrics=risk_metrics,
                               risk_recommendations=risk_recommendations,
                               detailed_metrics=detailed_metrics,
                               risk_chart_data=risk_chart_data,
                               drawdown_chart_data=drawdown_chart_data,
                               concentration_chart_data=concentration_chart_data,
                               current_period=period,
                               is_demo_mode=is_demo_mode,
                               auto_refresh=True)

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Risk analysis error: {e}', 'RiskAnalysis')
        # Fallback to DEMO data on error (NOT empty)
        return render_template('statistics/risk_analysis.html',
                               risk_metrics=get_demo_risk_metrics(),
                               risk_recommendations=get_demo_risk_recommendations(),
                               detailed_metrics=get_demo_detailed_risk_metrics(),
                               risk_chart_data=get_demo_risk_chart_data(),
                               drawdown_chart_data=get_demo_drawdown_chart_data(),
                               concentration_chart_data=get_demo_concentration_chart_data(),
                               current_period=period,
                               is_demo_mode=True,
                               auto_refresh=True)
    finally:
        conn.close()

@analytics_bp.route('/trend_analysis')
@login_required
@hybrid_compatible
def trend_analysis():
    """Optimized Trend Analysis Dashboard"""
    period = request.args.get('period', 'monthly')
    is_demo_mode = not get_mt5_connection_status()

    conn = None
    try:
        conn = get_db_connection()
        df = get_trades_by_period(conn, period)

        if df.empty:
            # QUICK RETURN - Use demo data for empty datasets
            return render_template('statistics/trend_analysis.html',
                                   trend_metrics=get_demo_trend_metrics(),
                                   trend_insights={
                                       'outlook': 'Bullish',
                                       'summary': 'Demo data showing sample trends',
                                       'recommendation': 'Connect MT5 for real analysis'
                                   },
                                   equity_trend_data={
                                       'dates': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05'],
                                       'equity': [10000, 11500, 12500, 11800, 13200],
                                       'trend': [10000, 11200, 12400, 11600, 12800]
                                   },
                                   trend_distribution=[
                                       {'name': 'Uptrend', 'value': 60},
                                       {'name': 'Sideways', 'value': 25},
                                       {'name': 'Downtrend', 'value': 15}
                                   ],
                                   monthly_trend_data={
                                       'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                                       'pnl': [1500, 1000, -700, 1400, 1100],
                                       'colors': ['success', 'success', 'danger', 'success', 'success']
                                   },
                                   pattern_data={
                                       'values': [1, -1, 1, 1, -1, 1, -1, -1, 1, 1],
                                       'sequence': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                                   },
                                   current_period=period,
                                   is_demo_mode=True,
                                   auto_refresh=True)

        # ONLY calculate if we have real data
        trend_metrics = calculate_trend_metrics(df)
        trend_insights = generate_trend_insights(trend_metrics, df)
        equity_trend_data = generate_equity_trend_data(df)
        trend_distribution = calculate_trend_distribution(df)
        monthly_trend_data = generate_monthly_trend_data(df)
        pattern_data = generate_pattern_analysis_data(df)

        return render_template('statistics/trend_analysis.html',
                               trend_metrics=trend_metrics,
                               trend_insights=trend_insights,
                               equity_trend_data=equity_trend_data,
                               trend_distribution=trend_distribution,
                               monthly_trend_data=monthly_trend_data,
                               pattern_data=pattern_data,
                               current_period=period,
                               is_demo_mode=is_demo_mode,
                               auto_refresh=True)

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Trend analysis error: {e}', 'TrendAnalysis')
        # Quick fallback to demo data
        return render_template('statistics/trend_analysis.html',
                               trend_metrics=get_demo_trend_metrics(),
                               trend_insights={
                                   'outlook': 'Bullish',
                                   'summary': 'Demo data - system error occurred',
                                   'recommendation': 'Check connection and try again'
                               },
                               equity_trend_data={
                                   'dates': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05'],
                                   'equity': [10000, 11500, 12500, 11800, 13200],
                                   'trend': [10000, 11200, 12400, 11600, 12800]
                               },
                               trend_distribution=[
                                   {'name': 'Uptrend', 'value': 60},
                                   {'name': 'Sideways', 'value': 25},
                                   {'name': 'Downtrend', 'value': 15}
                               ],
                               monthly_trend_data={
                                   'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                                   'pnl': [1500, 1000, -700, 1400, 1100],
                                   'colors': ['success', 'success', 'danger', 'success', 'success']
                               },
                               pattern_data={
                                   'values': [1, -1, 1, 1, -1, 1, -1, -1, 1, 1],
                                   'sequence': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                               },
                               current_period=period,
                               is_demo_mode=True,
                               auto_refresh=True)
    finally:
        if conn:
            conn.close()

@analytics_bp.route('/quantum_ai_qa')
@login_required
def quantum_ai_qa():
    """Quantum Professional Journal AI Q&A Dashboard"""
    return render_template('ai_qa.html')

@analytics_bp.route('/performance_metrics')
@login_required
def performance_metrics():
    """Performance metrics dashboard"""
    from flask import redirect, url_for
    return redirect(url_for('analytics.statistics_dashboard'))

# Analytics API Routes
@analytics_bp.route('/api/stats/<period>')
@login_required
def api_stats(period):
    """Professional API endpoint for trading statistics"""
    try:
        conn = get_db_connection()

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        elif period == '3months':
            start_date = end_date - timedelta(days=90)
        elif period == '6months':
            start_date = end_date - timedelta(days=180)
        elif period == '1year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime(1970, 1, 1)  # All time

        query = '''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ? 
            ORDER BY exit_time DESC
        '''
        df = pd.read_sql(query, conn, params=(start_date,))

        stats = stats_generator.generate_trading_statistics(df, period.capitalize()) if not df.empty else create_empty_stats()
        return jsonify(stats)

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional API stats error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@analytics_bp.route('/api/equity_curve')
@login_required
def api_equity_curve():
    """Professional equity curve API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('''
            SELECT timestamp, equity, balance 
            FROM account_history 
            ORDER BY timestamp
        ''', conn)

        if df.empty:
            # Generate professional demo equity curve
            base_equity = 10000
            timestamps = []
            equity = []
            balance = []

            for i in range(90):  # 90 days of data
                date = (datetime.now() - timedelta(days=89-i)).strftime('%Y-%m-%d')
                timestamps.append(date)

                # Simulate realistic equity curve with trends
                daily_change = np.random.normal(50, 200)  # Normal distribution
                base_equity += daily_change
                base_equity = max(5000, base_equity)  # Prevent going too low

                equity.append(round(base_equity, 2))
                balance.append(round(base_equity * 0.95, 2))  # Balance slightly below equity

            return jsonify({
                'timestamps': timestamps,
                'equity': equity,
                'balance': balance
            })

        return jsonify({
            'timestamps': df['timestamp'].astype(str).tolist(),
            'equity': df['equity'].tolist(),
            'balance': df['balance'].tolist()
        })

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional equity curve API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@analytics_bp.route('/api/trade_results_data')
@login_required
def api_trade_results_data():
    """Professional trade results API"""
    period = request.args.get('period', 'monthly')

    try:
        conn = get_db_connection()

        # Date filtering based on period
        end_date = datetime.now()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=365)

        query = '''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ?
            ORDER BY exit_time DESC
        '''
        df = pd.read_sql(query, conn, params=(start_date,))

        trades_data = df.to_dict('records') if not df.empty else []
        return jsonify({'trades': trades_data})

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional trade results API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@analytics_bp.route('/api/calendar/<int:year>/<int:month>')
@login_required
def api_calendar(year, month):
    """Professional calendar API"""
    try:
        calendar_data = calendar_dashboard.get_monthly_calendar(year, month)
        return jsonify(calendar_data)
    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional calendar API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/calendar_pnl')
@login_required
def api_calendar_pnl():
    """Professional calendar PnL API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('''
            SELECT date, daily_pnl, closed_trades, win_rate, winning_trades, losing_trades
            FROM calendar_pnl 
            ORDER BY date
        ''', conn)

        calendar_data = df.to_dict('records') if not df.empty else []
        return jsonify({'calendar': calendar_data})

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional calendar PnL API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@analytics_bp.route('/api/profit_loss_distribution')
@login_required
def api_profit_loss_distribution():
    """Professional P/L distribution API"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('SELECT profit FROM trades WHERE status = "CLOSED"', conn)

        if df.empty:
            return jsonify({'winning': 0, 'losing': 0, 'break_even': 0})

        winning = int((df['profit'] > 0).sum())
        losing = int((df['profit'] < 0).sum())
        break_even = int((df['profit'] == 0).sum())

        return jsonify({
            'winning': winning,
            'losing': losing,
            'break_even': break_even
        })

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Professional P/L distribution API error: {e}', 'API')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Helper functions
def get_trades_by_period(conn, period):
    """Get trades filtered by time period - HYBRID COMPATIBLE VERSION"""
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
        # CHANGED: Use hybrid dataframe fetch for "All time"
        return conn_fetch_dataframe(conn, 'SELECT * FROM trades')

    # CHANGED: Use hybrid dataframe fetch with parameters
    query = 'SELECT * FROM trades WHERE entry_time >= ?'
    return conn_fetch_dataframe(conn, query, params=(start_date,))

def calculate_symbol_performance(df):
    """Calculate symbol performance using existing metrics"""
    if df.empty:
        return []

    symbol_stats = []
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]

        symbol_stats.append({
            'symbol': symbol,
            'trade_count': len(symbol_df),
            'win_rate': len(symbol_df[symbol_df['profit'] > 0]) / len(symbol_df) * 100 if len(symbol_df) > 0 else 0,
            'net_pnl': symbol_df['profit'].sum(),
            'avg_pnl': symbol_df['profit'].mean(),
            'best_trade': symbol_df['profit'].max(),
            'worst_trade': symbol_df['profit'].min(),
            'total_volume': symbol_df['volume'].sum() if 'volume' in symbol_df.columns else 0
        })

    return sorted(symbol_stats, key=lambda x: x['net_pnl'], reverse=True)

def calculate_strategy_performance(df):
    """Calculate strategy performance using existing analytics"""
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