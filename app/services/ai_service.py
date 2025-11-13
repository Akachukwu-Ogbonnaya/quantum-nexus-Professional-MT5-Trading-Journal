import pandas as pd
import numpy as np
from utils import add_log
from utils.database import get_db_connection
from datetime import datetime, timedelta

def generate_ai_coach_advice(stats, market_context, timeframe):
    win_rate = stats.get('win_rate', 0)
    profit_factor = stats.get('profit_factor', 0)
    total_trades = stats.get('total_trades', 0)
    net_profit = stats.get('net_profit', 0)
    avg_rr = stats.get('avg_rr', 0)

    advice = []

    if win_rate < 40:
        advice.append(
            "Your win rate is below 40%. Focus on improving entry timing and trade selection. Consider waiting for higher probability setups.")
    elif win_rate > 60:
        advice.append(
            "Excellent win rate above 60%! Your trade selection is strong. Consider scaling up position sizes gradually while maintaining risk management.")
    else:
        advice.append("Solid win rate. Focus on consistency and risk management to improve profitability.")

    if avg_rr < 1.0:
        advice.append(
            "Your risk-reward ratio is below 1.0. Work on letting winners run and cutting losses quickly. Aim for at least 1.5:1 R:R ratio.")
    elif avg_rr > 2.0:
        advice.append(
            "Outstanding risk-reward management! Your ability to let profits run while controlling losses is excellent.")

    if profit_factor < 1.0:
        advice.append(
            "Profit factor below 1.0 indicates overall unprofitability. Review your strategy and risk management approach.")
    elif profit_factor > 2.0:
        advice.append("Exceptional profit factor! Your trading edge is well-defined and effectively executed.")

    if total_trades < 10:
        advice.append(
            "Low trade volume detected. Consider whether you're being too selective or missing opportunities. Review your trading plan.")
    elif total_trades > 50 and timeframe == 'weekly':
        advice.append(
            "High trade frequency. Ensure you're not overtrading. Quality over quantity often leads to better results.")

    return " ".join(advice)

def calculate_risk_metrics(trades_df, account_history):
    if trades_df.empty:
        return {
            'drawdown': 0,
            'volatility': 0,
            'risk_score': 0,
            'position_concentration': 0,
            'recent_loss_streak': 0
        }

    drawdown = 0
    if not account_history.empty:
        equity_curve = account_history['equity'].tolist()
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            current_dd = (peak - equity) / peak * 100
            if current_dd > drawdown:
                drawdown = current_dd

    recent_profits = trades_df['profit'].tolist() if not trades_df.empty else []
    volatility = np.std(recent_profits) if recent_profits else 0

    loss_streak = 0
    current_streak = 0
    for profit in recent_profits:
        if profit < 0:
            current_streak += 1
            loss_streak = max(loss_streak, current_streak)
        else:
            current_streak = 0

    if not trades_df.empty:
        symbol_counts = trades_df['symbol'].value_counts()
        concentration = symbol_counts.iloc[0] / len(trades_df) * 100 if len(trades_df) > 0 else 0
    else:
        concentration = 0

    risk_score = min(100, drawdown * 2 + volatility / 10 + concentration / 2 + loss_streak * 10)

    return {
        'drawdown': round(drawdown, 2),
        'volatility': round(volatility, 2),
        'risk_score': round(risk_score, 2),
        'position_concentration': round(concentration, 2),
        'recent_loss_streak': loss_streak
    }

def generate_risk_assessment(risk_metrics):
    risk_score = risk_metrics['risk_score']
    drawdown = risk_metrics['drawdown']

    if risk_score < 25:
        level = "LOW"
        recommendations = [
            "Your risk exposure is well-controlled",
            "Consider gradual position size increases for quality setups",
            "Maintain current risk management practices"
        ]
    elif risk_score < 50:
        level = "MODERATE"
        recommendations = [
            "Monitor position sizes and correlation",
            "Ensure stop-losses are properly placed",
            "Consider reducing trade frequency if drawdown increases"
        ]
    elif risk_score < 75:
        level = "HIGH"
        recommendations = [
            "Reduce position sizes by 25-50% immediately",
            "Implement stricter daily loss limits",
            "Focus only on highest probability setups",
            "Review recent losing trades for patterns"
        ]
    else:
        level = "EXTREME"
        recommendations = [
            "REDUCE POSITION SIZES BY 50-75% IMMEDIATELY",
            "Implement maximum daily loss limit of 2%",
            "Trade only 1-2 highest conviction setups per day",
            "Consider taking a break to review strategy"
        ]

    return {
        'level': level,
        'score': risk_score,
        'recommendations': recommendations
    }

def generate_market_analysis(top_symbols, best_hours, analysis_type):
    analysis = f"Market Analysis for {analysis_type.upper()} Trading:\n\n"

    if top_symbols:
        analysis += "Based on your trading history, your most active symbols are:\n"
        for symbol in top_symbols[:3]:
            analysis += f"- {symbol['symbol']}: {symbol['trade_count']} trades, Avg PnL: ${symbol['avg_profit']:.2f}\n"
        analysis += "\n"

    if best_hours:
        best_hour = best_hours[0] if best_hours else {}
        analysis += f"Your most profitable trading hour: {best_hour.get('hour', 'N/A')}:00\n"
        analysis += f"Average profit during this hour: ${best_hour.get('avg_profit', 0):.2f}\n\n"

    if analysis_type == 'intraday':
        analysis += "Intraday Strategy Focus:\n"
        analysis += "- Monitor key support/resistance levels\n"
        analysis += "- Use shorter timeframes for entry timing\n"
        analysis += "- Implement tight stop-losses\n"
        analysis += "- Take partial profits at technical levels\n"
    elif analysis_type == 'swing':
        analysis += "Swing Trading Strategy Focus:\n"
        analysis += "- Focus on daily chart patterns\n"
        analysis += "- Use wider stops for volatility\n"
        analysis += "- Position size for 2-5 day holds\n"
        analysis += "- Monitor macroeconomic developments\n"
    else:
        analysis += "Position Trading Strategy Focus:\n"
        analysis += "- Analyze weekly/monthly charts\n"
        analysis += "- Fundamental analysis is key\n"
        analysis += "- Use position sizing for longer holds\n"
        analysis += "- Monitor trend changes carefully\n"

    return analysis

def generate_psychology_analysis(mood_data, psychology_logs, performance_data):
    emotion = mood_data.get('emotion', 'neutral')
    confidence = mood_data.get('confidence_level', 3)
    stress = mood_data.get('stress_level', 3)

    analysis = "Trading Psychology Analysis:\n\n"

    if emotion in ['anxious', 'frustrated', 'stressed']:
        analysis += "⚠️  Emotional State Alert:\n"
        analysis += "Your current emotional state may impact trading decisions.\n"
        analysis += "- Consider reducing position sizes temporarily\n"
        analysis += "- Focus on deep breathing before entering trades\n"
        analysis += "- Review your trading plan for confidence\n"
    elif emotion in ['confident', 'calm', 'focused']:
        analysis += "✅  Optimal Mental State:\n"
        analysis += "You're in a good mental state for trading.\n"
        analysis += "- Maintain current emotional discipline\n"
        analysis += "- Stick to your proven strategies\n"
        analysis += "- Avoid overconfidence in winning streaks\n"

    analysis += "\n"

    if confidence < 3:
        analysis += "Confidence Building Tips:\n"
        analysis += "- Review your successful trades\n"
        analysis += "- Paper trade to rebuild confidence\n"
        analysis += "- Focus on process over outcomes\n"

    if stress > 4:
        analysis += "Stress Management:\n"
        analysis += "- Implement strict risk management\n"
        analysis += "- Take regular breaks during sessions\n"
        analysis += "- Consider meditation or exercise\n"

    if psychology_logs:
        analysis += f"\nBased on {len(psychology_logs)} psychology entries, "
        analysis += "maintain consistent emotional tracking for better self-awareness."

    return analysis

def get_question_context(conn, category, question):
    context = {'context_type': 'general'}

    try:
        if category == 'performance':
            df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)
            if not df.empty:
                stats = stats_generator.generate_trading_statistics(df)
                context.update({
                    'context_type': 'performance',
                    'win_rate': stats.get('win_rate', 0),
                    'profit_factor': stats.get('profit_factor', 0),
                    'total_trades': stats.get('total_trades', 0),
                    'recent_performance': stats.get('net_profit', 0)
                })

        elif category == 'risk':
            risk_data = pd.read_sql('''
                SELECT sl_price, profit, volume, symbol 
                FROM trades 
                WHERE status = "CLOSED" 
                ORDER BY entry_time DESC 
                LIMIT 50
            ''', conn)
            context.update({
                'context_type': 'risk',
                'recent_trades_count': len(risk_data),
                'avg_position_size': risk_data['volume'].mean() if not risk_data.empty else 0
            })

        elif category == 'psychology':
            try:
                psych_data = pd.read_sql('''
                    SELECT emotion_label, confidence_level, stress_level
                    FROM psychology_logs 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', conn, params=(current_user.id,))
                context.update({
                    'context_type': 'psychology',
                    'recent_moods': psych_data.to_dict('records') if not psych_data.empty else []
                })
            except:
                pass

    except Exception as e:
        add_log('ERROR', f'Question context error: {e}', 'AI_Q&A')

    return context

def generate_ai_response(question, category, context_data):
    responses = {
        'performance': [
            "Based on your trading performance, I recommend focusing on consistency in your approach.",
            "Your performance data shows areas for improvement in risk management and trade timing.",
            "Excellent performance detected! Consider scaling your successful strategies."
        ],
        'risk': [
            "Your risk management appears adequate, but there's room for improvement in position sizing.",
            "Consider implementing stricter stop-loss rules based on recent volatility.",
            "Risk exposure is well-managed. Maintain current risk parameters."
        ],
        'strategy': [
            "Your trading strategy shows promise. Consider backtesting additional market conditions.",
            "Strategy optimization could improve your edge. Review entry and exit criteria.",
            "Solid strategic approach. Focus on execution consistency."
        ],
        'psychology': [
            "Trading psychology is crucial. Consider maintaining an emotion journal.",
            "Your mindset appears balanced. Continue focusing on disciplined execution.",
            "Emotional control can be improved through mindfulness practices."
        ],
        'general': [
            "Based on your trading data, I recommend reviewing your journal regularly for patterns.",
            "Continuous learning and adaptation are key to long-term trading success.",
            "Consider diversifying your strategies across different market conditions."
        ]
    }

    category_responses = responses.get(category, responses['general'])

    if context_data.get('context_type') == 'performance':
        win_rate = context_data.get('win_rate', 0)
        if win_rate > 60:
            response = category_responses[2] if len(category_responses) > 2 else category_responses[0]
        elif win_rate < 40:
            response = category_responses[1] if len(category_responses) > 1 else category_responses[0]
        else:
            response = category_responses[0]
    else:
        response = category_responses[0]

    return f"🤖 Quantum AI Analysis:\n\n{response}\n\nContext: {context_data.get('context_type', 'general analysis')}"

def store_ai_interaction(question, answer, category):
    add_log('INFO', f'AI Q&A: {category} - Q: {question[:100]}...', 'AI_Q&A')