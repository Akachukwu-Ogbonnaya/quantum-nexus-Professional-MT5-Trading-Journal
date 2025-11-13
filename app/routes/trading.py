from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.utils.database import get_db_connection, get_universal_connection, conn_fetch_dataframe, universal_execute
from app.utils.hybrid import hybrid_compatible
from app.utils.stats import stats_generator, create_empty_stats
from app.utils.logging import add_log
import pandas as pd
from datetime import datetime

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/journal')
@login_required
@hybrid_compatible
def journal():
    """Professional trade journal with advanced calculations - HYBRID COMPATIBLE VERSION"""
    conn = get_universal_connection()
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page

        # Get filter parameters
        symbol_filter = request.args.get('symbol', '')
        status_filter = request.args.get('status', '')

        # Build query
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []

        if symbol_filter:
            query += ' AND symbol = ?'
            params.append(symbol_filter)

        if status_filter:
            query += ' AND status = ?'
            params.append(status_filter)

        query += ' ORDER BY entry_time DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])

        # Use hybrid dataframe fetch
        trades = conn_fetch_dataframe(conn, query, params=params)
        trades_dict = trades.to_dict('records') if not trades.empty else []

        # Convert string dates to datetime objects
        from app.utils.helpers import convert_trade_dates
        trades_dict = convert_trade_dates(trades_dict)

        # Get unique symbols for filter dropdown
        symbols = conn_fetch_dataframe(conn, 'SELECT DISTINCT symbol FROM trades ORDER BY symbol')
        symbols_list = symbols['symbol'].tolist() if not symbols.empty else []

        # Get total count for pagination
        count_query = 'SELECT COUNT(*) as total FROM trades WHERE 1=1'
        count_params = []

        if symbol_filter:
            count_query += ' AND symbol = ?'
            count_params.append(symbol_filter)

        if status_filter:
            count_query += ' AND status = ?'
            count_params.append(status_filter)

        cursor = conn.cursor()
        universal_execute(cursor, count_query, count_params)
        total_count = cursor.fetchone()[0]

        # Calculate professional statistics
        df_all_trades = conn_fetch_dataframe(conn, 'SELECT * FROM trades WHERE status = "CLOSED"')

        # SAFE STATS GENERATION
        if not df_all_trades.empty:
            try:
                stats = stats_generator.generate_trading_statistics(df_all_trades)
                # Ensure all required stats fields exist
                required_stats = ['max_drawdown', 'win_rate', 'profit_factor', 'total_trades',
                                  'gross_profit', 'gross_loss', 'sharpe_ratio', 'avg_win',
                                  'avg_loss', 'largest_win', 'largest_loss', 'current_drawdown',
                                  'expectancy', 'risk_reward_ratio']

                # Convert stats to dict if it's an object
                if not isinstance(stats, dict):
                    stats_dict = {}
                    for field in required_stats:
                        stats_dict[field] = getattr(stats, field, 0.0)
                    stats = stats_dict
                else:
                    # Ensure all fields exist in dict
                    for field in required_stats:
                        if field not in stats:
                            stats[field] = 0.0
            except Exception as stats_error:
                add_log('ERROR', f'Stats calculation error: {stats_error}', 'Journal')
                stats = create_empty_stats()
        else:
            stats = create_empty_stats()

        # Calculate floating P&L from open positions
        open_positions = conn_fetch_dataframe(conn, 'SELECT * FROM trades WHERE status = "OPEN"')
        floating_pnl = open_positions['floating_pnl'].sum() if not open_positions.empty else 0

        # Calculate additional metrics for template
        open_positions_data = open_positions.to_dict('records') if not open_positions.empty else []
        closed_trades_data = df_all_trades.to_dict('records') if not df_all_trades.empty else []

        # Calculate counts for display
        open_positions_count = len(open_positions_data)
        closed_trades_count = len(closed_trades_data)

    except Exception as e:
        add_log('ERROR', f'Journal error: {e}', 'Journal')
        trades_dict, symbols_list, total_count = [], [], 0
        stats = create_empty_stats()
        floating_pnl = 0
        open_positions_data = []
        closed_trades_data = []
        open_positions_count = 0
        closed_trades_count = 0
    finally:
        conn.close()

    return render_template('journal.html',
                           trades=trades_dict,
                           symbols=symbols_list,
                           current_page=page,
                           total_pages=(total_count + per_page - 1) // per_page,
                           symbol_filter=symbol_filter,
                           status_filter=status_filter,
                           stats=stats,
                           floating_pnl=floating_pnl,
                           open_positions=open_positions_data,
                           closed_trades=closed_trades_data,
                           open_positions_count=open_positions_count,
                           closed_trades_count=closed_trades_count,
                           mt5_connected=True,
                           current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@trading_bp.route('/api/update_trade_comment/<ticket_id>', methods=['POST'])
@login_required
def update_trade_comment(ticket_id):
    """Update trade comment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data = request.get_json()
        comment = data.get('comment', '')

        cursor.execute('''
            UPDATE trades SET comment = ? WHERE ticket_id = ?
        ''', (comment, ticket_id))

        conn.commit()
        add_log('INFO', f'Trade {ticket_id} comment updated', 'TradeJournal')

        return jsonify(success=True, message='Comment updated successfully')

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade comment update error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()

@trading_bp.route('/api/edit_trade/<ticket_id>', methods=['POST'])
@login_required
def edit_trade(ticket_id):
    """Edit trade details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data = request.get_json()

        # Update trade fields
        cursor.execute('''
            UPDATE trades SET 
                symbol = ?, type = ?, volume = ?, entry_price = ?,
                sl_price = ?, tp_price = ?, strategy = ?, comment = ?
            WHERE ticket_id = ?
        ''', (
            data.get('symbol'),
            data.get('type'),
            data.get('volume'),
            data.get('entry_price'),
            data.get('sl_price'),
            data.get('tp_price'),
            data.get('strategy'),
            data.get('comment'),
            ticket_id
        ))

        conn.commit()
        add_log('INFO', f'Trade {ticket_id} details updated', 'TradeJournal')

        return jsonify(success=True, message='Trade updated successfully')

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade edit error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()

@trading_bp.route('/api/duplicate_trade/<ticket_id>', methods=['POST'])
@login_required
def duplicate_trade(ticket_id):
    """Duplicate an existing trade"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get original trade data
        cursor.execute('''
            SELECT symbol, type, volume, entry_price, sl_price, tp_price, strategy, comment
            FROM trades WHERE ticket_id = ?
        ''', (ticket_id,))

        trade = cursor.fetchone()

        if trade:
            # Insert as new trade with current timestamp
            cursor.execute('''
                INSERT INTO trades 
                (ticket_id, symbol, type, volume, entry_price, sl_price, tp_price, 
                 strategy, comment, entry_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN', CURRENT_TIMESTAMP)
            ''', (
                f"DUPLICATE_{int(time.time())}",  # New ticket ID
                trade[0],  # symbol
                trade[1],  # type
                trade[2],  # volume
                trade[3],  # entry_price
                trade[4],  # sl_price
                trade[5],  # tp_price
                trade[6],  # strategy
                f"Duplicate of {ticket_id} - {trade[7]}"  # comment
            ))

            conn.commit()
            add_log('INFO', f'Trade {ticket_id} duplicated', 'TradeJournal')

            return jsonify(success=True, message='Trade duplicated successfully')
        else:
            return jsonify(success=False, message='Original trade not found'), 404

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Trade duplicate error: {e}', 'TradeJournal')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()

@trading_bp.route('/psychology_log')
@login_required
def psychology_log():
    """Trading Psychology Log Dashboard"""
    # Create psychology logs table if it doesn't exist
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS psychology_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            trade_id TEXT,
            log_date DATETIME,
            emotion_level INTEGER,
            emotion_label TEXT,
            confidence_level INTEGER,
            stress_level INTEGER,
            discipline_level INTEGER,
            thoughts TEXT,
            improvement_areas TEXT,
            psychology_factors TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

    return render_template('psychology_log.html')

@trading_bp.route('/api/psychology_logs', methods=['GET', 'POST'])
@login_required
def psychology_logs_api():
    """Psychology Logs API endpoint - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            # Save new psychology log
            data = request.get_json()

            universal_execute(cursor, '''
                INSERT INTO psychology_logs 
                (user_id, trade_id, log_date, emotion_level, emotion_label, 
                 confidence_level, stress_level, discipline_level, thoughts, 
                 improvement_areas, psychology_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data.get('trade_id'),
                data.get('log_date'),
                data.get('emotion_level'),
                data.get('emotion_label'),
                data.get('confidence_level'),
                data.get('stress_level'),
                data.get('discipline_level'),
                data.get('thoughts'),
                data.get('improvement_areas'),
                json.dumps(data.get('psychology_factors', []))
            ))

            conn.commit()
            add_log('INFO', f'Psychology log saved for trade {data.get("trade_id")}', 'Psychology')

            return jsonify(success=True, message='Psychology log saved successfully')

        else:
            # Get psychology logs for current user
            universal_execute(cursor, '''
                SELECT * FROM psychology_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            ''', (current_user.id,))

            logs = cursor.fetchall()

            # Convert to dictionary format
            logs_dict = []
            for log in logs:
                logs_dict.append({
                    'id': log[0],
                    'trade_id': log[2],
                    'log_date': log[3],
                    'emotion_level': log[4],
                    'emotion_label': log[5],
                    'confidence_level': log[6],
                    'stress_level': log[7],
                    'discipline_level': log[8],
                    'thoughts': log[9],
                    'improvement_areas': log[10],
                    'psychology_factors': json.loads(log[11]) if log[11] else [],
                    'created_at': log[12]
                })

            return jsonify(logs=logs_dict)

    except Exception as e:
        conn.rollback()
        add_log('ERROR', f'Psychology logs error: {e}', 'Psychology')
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()

@trading_bp.route('/api/psychology_stats')
@login_required
def psychology_stats():
    """Psychology Statistics API - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()
        cursor = conn.cursor()

        # Get emotion distribution
        universal_execute(cursor, '''
            SELECT emotion_label, COUNT(*) as count 
            FROM psychology_logs 
            WHERE user_id = ? 
            GROUP BY emotion_label
        ''', (current_user.id,))

        emotion_stats = cursor.fetchall()

        # Get average metrics
        universal_execute(cursor, '''
            SELECT 
                AVG(confidence_level) as avg_confidence,
                AVG(stress_level) as avg_stress, 
                AVG(discipline_level) as avg_discipline
            FROM psychology_logs 
            WHERE user_id = ?
        ''', (current_user.id,))

        avg_metrics = cursor.fetchone()

        return jsonify({
            'emotion_distribution': dict(emotion_stats),
            'average_metrics': {
                'confidence': round(avg_metrics[0] or 0, 1),
                'stress': round(avg_metrics[1] or 0, 1),
                'discipline': round(avg_metrics[2] or 0, 1)
            }
        })

    except Exception as e:
        add_log('ERROR', f'Psychology stats error: {e}', 'Psychology')
        return jsonify(error=str(e)), 500
    finally:
        conn.close()