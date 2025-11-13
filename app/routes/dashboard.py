from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils.database import get_db_connection
from app.utils.stats import stats_generator, create_empty_stats
from app.utils.sync import data_synchronizer
from app.utils.calendar import calendar_dashboard
from app.utils.hybrid import hybrid_compatible
import pandas as pd
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
@hybrid_compatible
def professional_dashboard():
    """Enhanced professional dashboard with safe dictionary handling"""
    try:
        conn = get_db_connection()

        # Get comprehensive statistics
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
        stats = stats_generator.generate_trading_statistics(df) if not df.empty else create_empty_stats()

        # Get account data
        account_data = data_synchronizer.get_account_data()

        # Get current month calendar
        now = datetime.now()
        calendar_data = calendar_dashboard.get_monthly_calendar(now.year, now.month)

        # Get recent trades for dashboard
        recent_trades = pd.read_sql(
            'SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10', conn
        ).to_dict('records') if not df.empty else []

        # Get open positions
        open_positions = pd.read_sql(
            'SELECT * FROM trades WHERE status = "OPEN" ORDER BY entry_time DESC', conn
        ).to_dict('records')

    except Exception as e:
        from app.utils.logging import add_log
        add_log('ERROR', f'Dashboard error: {e}', 'Dashboard')
        stats, account_data, calendar_data, recent_trades, open_positions = create_empty_stats(), {}, {}, [], []
    finally:
        conn.close()

    return render_template('dashboard.html',
                         stats=stats,
                         account_data=account_data,
                         calendar_data=calendar_data,
                         recent_trades=recent_trades,
                         open_positions=open_positions,
                         current_year=datetime.now().year,
                         current_month=datetime.now().month)

@dashboard_bp.route('/quick/journal')
@login_required
def quick_journal():
    """Quick journal access"""
    from flask import redirect, url_for
    return redirect(url_for('journal.journal'))

@dashboard_bp.route('/quick/trade_plan')
@login_required
def quick_trade_plan():
    """Quick trade plan access"""
    from flask import redirect, url_for
    return redirect(url_for('trade_plan.trade_plan'))