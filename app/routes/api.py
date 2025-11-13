from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.utils.database import get_db_connection, get_universal_connection, conn_fetch_dataframe
from app.utils.sync import data_synchronizer
from app.utils.stats import stats_generator, create_empty_stats
from app.utils.calendar import calendar_dashboard
from app.utils.hybrid import hybrid_compatible
from app.utils.logging import add_log, advanced_logger
from app.utils.ai import (
    generate_ai_coach_advice,
    calculate_risk_metrics,
    generate_risk_assessment,
    generate_market_analysis,
    generate_psychology_analysis,
    get_question_context,
    generate_ai_response,
    store_ai_interaction
)
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/sync_now')
@login_required
def api_sync_now():
    """Professional manual sync API"""
    try:
        print("🔄 Manual sync requested via API")
        success = data_synchronizer.sync_with_mt5(force=True)

        if success:
            # Get updated stats - FIXED: Convert int64 to regular int
            conn = get_db_connection()
            trades_count = int(pd.read_sql('SELECT COUNT(*) as count FROM trades', conn).iloc[0]['count'])
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Sync completed! Imported {trades_count} trades.',
                'trades_count': trades_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Sync failed. Check MT5 connection.'
            })

    except Exception as e:
        print(f"❌ Sync error: {e}")
        return jsonify({
            'success': False,
            'message': f'Sync error: {str(e)}'
        })

@api_bp.route('/api/sync_status')
@login_required
def api_sync_status():
    """Get current sync status"""
    try:
        conn = get_db_connection()
        # FIXED: Convert int64 to regular int
        trades_count = int(pd.read_sql('SELECT COUNT(*) as count FROM trades', conn).iloc[0]['count'])
        open_positions = int(
            pd.read_sql('SELECT COUNT(*) as count FROM trades WHERE status = "OPEN"', conn).iloc[0]['count'])
        conn.close()

        return jsonify({
            'trades_total': trades_count,
            'open_positions': open_positions,
            'last_sync': data_synchronizer.last_sync.isoformat() if data_synchronizer.last_sync else None,
            'mt5_connected': False
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@api_bp.route('/api/logs')
@login_required
def api_logs():
    """Professional logs API"""
    return jsonify({'logs': advanced_logger.log_messages[-100:]})

@api_bp.route('/api/connection_status')
def api_connection_status():
    """API endpoint to check current connection status"""
    from app.utils.mt5 import get_mt5_connection_status
    is_demo = not get_mt5_connection_status()
    return jsonify({
        'is_demo_mode': is_demo,
        'status': 'demo' if is_demo else 'live',
        'timestamp': datetime.now().isoformat(),
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# AI API Routes
@api_bp.route('/api/ai/get_user_stats')
@login_required
def api_ai_user_stats():
    """Get comprehensive user statistics for AI analysis"""
    try:
        conn = get_db_connection()

        # Get trading statistics
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
        stats = stats_generator.generate_trading_statistics(df) if not df.empty else create_empty_stats()

        # Get recent trades for context
        recent_trades = pd.read_sql(
            'SELECT * FROM trades ORDER BY entry_time DESC LIMIT 20', conn
        ).to_dict('records') if not df.empty else []

        # Get account data
        from app.utils.sync import data_synchronizer
        account_data = data_synchronizer.get_account_data()

        # Get psychology logs if available
        psychology_stats = {}
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    AVG(confidence_level) as avg_confidence,
                    AVG(stress_level) as avg_stress,
                    AVG(discipline_level) as avg_discipline
                FROM psychology_logs WHERE user_id = ?
            ''', (current_user.id,))
            psych_result = cursor.fetchone()
            if psych_result:
                psychology_stats = {
                    'avg_confidence': psych_result[0] or 0,
                    'avg_stress': psych_result[1] or 0,
                    'avg_discipline': psych_result[2] or 0
                }
        except:
            pass

        conn.close()

        return jsonify({
            'trading_stats': stats,
            'account_data': account_data,
            'psychology_stats': psychology_stats,
            'recent_trades_sample': recent_trades[:5],
            'total_trades_count': len(df) if not df.empty else 0
        })

    except Exception as e:
        add_log('ERROR', f'AI user stats error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/trade_analysis/<int:trade_id>')
@login_required
def api_ai_trade_analysis(trade_id):
    """Get specific trade data for AI analysis"""
    try:
        conn = get_db_connection()

        # Get the specific trade
        trade_df = pd.read_sql(
            'SELECT * FROM trades WHERE id = ? OR ticket_id = ?',
            conn, params=(trade_id, trade_id)
        )

        if trade_df.empty:
            return jsonify({'error': 'Trade not found'}), 404

        trade_data = trade_df.iloc[0].to_dict()

        # Get similar trades for context
        symbol = trade_data.get('symbol', '')
        similar_trades = pd.read_sql('''
            SELECT * FROM trades 
            WHERE symbol = ? AND status = "CLOSED" 
            ORDER BY entry_time DESC LIMIT 10
        ''', conn, params=(symbol,)).to_dict('records')

        conn.close()

        return jsonify({
            'trade': trade_data,
            'similar_trades': similar_trades,
            'analysis_context': {
                'symbol': symbol,
                'trade_type': trade_data.get('type'),
                'profitability': trade_data.get('profit', 0) > 0
            }
        })

    except Exception as e:
        add_log('ERROR', f'AI trade analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/coach_advice', methods=['POST'])
@login_required
def api_ai_coach_advice():
    """Get AI trading coach advice based on user data"""
    try:
        data = request.get_json()
        timeframe = data.get('timeframe', 'weekly')

        # Get comprehensive user data
        conn = get_db_connection()

        # Calculate date range based on timeframe
        end_date = datetime.now()
        if timeframe == 'daily':
            start_date = end_date - timedelta(days=1)
        elif timeframe == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif timeframe == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)

        # Get trades for the period
        trades_df = pd.read_sql('''
            SELECT * FROM trades 
            WHERE status = "CLOSED" AND exit_time >= ?
            ORDER BY exit_time DESC
        ''', conn, params=(start_date,))

        stats = stats_generator.generate_trading_statistics(trades_df, timeframe) if not trades_df.empty else create_empty_stats()

        # Get current market context (simplified)
        market_context = {
            'current_time': datetime.now().isoformat(),
            'timeframe': timeframe,
            'analysis_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        }

        conn.close()

        # Generate AI coach advice
        advice = generate_ai_coach_advice(stats, market_context, timeframe)

        return jsonify({
            'advice': advice,
            'timeframe': timeframe,
            'stats_snapshot': {
                'win_rate': stats.get('win_rate', 0),
                'profit_factor': stats.get('profit_factor', 0),
                'total_trades': stats.get('total_trades', 0),
                'net_profit': stats.get('net_profit', 0)
            },
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI coach advice error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/risk_assessment')
@login_required
def api_ai_risk_assessment():
    """Get AI-powered risk assessment"""
    try:
        conn = get_db_connection()

        # Get recent trades for risk analysis
        recent_trades = pd.read_sql('''
            SELECT * FROM trades 
            WHERE entry_time >= DATE('now', '-30 days')
            ORDER BY entry_time DESC
        ''', conn)

        # Get account history for drawdown analysis
        account_history = pd.read_sql('''
            SELECT equity, balance, timestamp 
            FROM account_history 
            WHERE timestamp >= DATE('now', '-30 days')
            ORDER BY timestamp
        ''', conn)

        conn.close()

        # Calculate risk metrics
        risk_metrics = calculate_risk_metrics(recent_trades, account_history)
        risk_assessment = generate_risk_assessment(risk_metrics)

        return jsonify({
            'risk_level': risk_assessment['level'],
            'risk_score': risk_assessment['score'],
            'recommendations': risk_assessment['recommendations'],
            'metrics': risk_metrics,
            'assessment_date': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI risk assessment error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/market_analysis', methods=['POST'])
@login_required
def api_ai_market_analysis():
    """Get AI-powered market analysis"""
    try:
        data = request.get_json()
        analysis_type = data.get('type', 'intraday')

        # Get user's trading preferences and history
        conn = get_db_connection()

        # Get most traded symbols
        symbol_stats = pd.read_sql('''
            SELECT symbol, COUNT(*) as trade_count, AVG(profit) as avg_profit
            FROM trades 
            WHERE status = "CLOSED"
            GROUP BY symbol 
            ORDER BY trade_count DESC 
            LIMIT 5
        ''', conn)

        # Get user's best performing timeframes
        performance_by_hour = pd.read_sql('''
            SELECT strftime('%H', entry_time) as hour, 
                   AVG(profit) as avg_profit,
                   COUNT(*) as trade_count
            FROM trades 
            WHERE status = "CLOSED"
            GROUP BY hour
            ORDER BY avg_profit DESC
        ''', conn)

        conn.close()

        # Generate market analysis based on user's trading style
        market_analysis = generate_market_analysis(
            symbol_stats.to_dict('records'),
            performance_by_hour.to_dict('records'),
            analysis_type
        )

        return jsonify({
            'analysis': market_analysis,
            'user_preferences': {
                'top_symbols': symbol_stats.to_dict('records'),
                'best_hours': performance_by_hour.to_dict('records')
            },
            'analysis_type': analysis_type,
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI market analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/psychology_analysis', methods=['POST'])
@login_required
def api_ai_psychology_analysis():
    """AI-powered trading psychology analysis"""
    try:
        data = request.get_json()
        mood_data = data.get('mood_data', {})

        # Get psychology logs if available
        conn = get_db_connection()

        psychology_logs = []
        try:
            psychology_logs = pd.read_sql('''
                SELECT * FROM psychology_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            ''', conn, params=(current_user.id,)).to_dict('records')
        except:
            pass

        # Get trading performance correlated with psychology
        performance_data = pd.read_sql('''
            SELECT date(exit_time) as trade_date, 
                   SUM(profit) as daily_pnl,
                   COUNT(*) as trade_count
            FROM trades 
            WHERE status = "CLOSED" AND exit_time >= DATE('now', '-30 days')
            GROUP BY trade_date
            ORDER BY trade_date
        ''', conn)

        conn.close()

        # Generate psychology analysis
        psychology_analysis = generate_psychology_analysis(
            mood_data,
            psychology_logs,
            performance_data.to_dict('records')
        )

        return jsonify({
            'analysis': psychology_analysis,
            'mood_data': mood_data,
            'has_psychology_history': len(psychology_logs) > 0
        })

    except Exception as e:
        add_log('ERROR', f'AI psychology analysis error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/ai/custom_question', methods=['POST'])
@login_required
def api_ai_custom_question():
    """Handle custom AI questions with trading context"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        category = data.get('category', 'general')

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # Get comprehensive user context
        conn = get_db_connection()

        # Get relevant data based on question category
        context_data = get_question_context(conn, category, question)

        conn.close()

        # Generate AI response
        ai_response = generate_ai_response(question, category, context_data)

        # Store the Q&A interaction (optional)
        store_ai_interaction(question, ai_response, category)

        return jsonify({
            'question': question,
            'answer': ai_response,
            'category': category,
            'context_used': context_data.get('context_type', 'general'),
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        add_log('ERROR', f'AI custom question error: {e}', 'AI_Q&A')
        return jsonify({'error': str(e)}), 500

@api_bp.route('/debug/routes')
def debug_routes():
    """Debug endpoint to see all registered routes"""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': rule.rule
        })
    return jsonify(routes)