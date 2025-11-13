from flask import Blueprint, send_file
from flask_login import login_required
from app.utils.database import get_db_connection
from app.utils.logging import add_log
import pandas as pd
from datetime import datetime
import io
import csv

export_bp = Blueprint('export', __name__)

@export_bp.route('/export/csv')
@login_required
def export_csv():
    """Professional CSV export"""
    try:
        conn = get_db_connection()
        df = pd.read_sql('SELECT * FROM trades ORDER BY entry_time DESC', conn)

        if df.empty:
            # Create professional demo CSV data
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Ticket', 'Symbol', 'Type', 'Volume', 'Entry', 'Exit', 'Profit', 'RR Ratio', 'Duration', 'Status'])
            writer.writerow([500001, 'EURUSD', 'BUY', '0.1', '1.0950', '1.0980', '30.0', '2.0', '2h 30m', 'CLOSED'])
            writer.writerow([500002, 'GBPUSD', 'SELL', '0.1', '1.2750', '1.2720', '30.0', '1.5', '1h 15m', 'CLOSED'])
            writer.writerow([500003, 'XAUUSD', 'BUY', '0.01', '1950.50', '1955.25', '47.5', '2.3', '4h 45m', 'CLOSED'])
        else:
            # Export professional data
            output = io.StringIO()
            df.to_csv(output, index=False)

        output.seek(0)
        filename = f"professional_mt5_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        add_log('ERROR', f'Professional CSV export error: {e}', 'Export')
        from flask import flash
        flash('Error exporting CSV', 'danger')
        from flask import redirect, url_for
        return redirect(url_for('dashboard.professional_dashboard'))

@export_bp.route('/export/pdf')
@login_required
def export_pdf():
    """Professional PDF export"""
    try:
        # Check if reportlab is available
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            reportlab_available = True
        except ImportError:
            reportlab_available = False
            from flask import flash
            flash('PDF export requires ReportLab installation', 'warning')
            return redirect(url_for('dashboard.professional_dashboard'))

        if not reportlab_available:
            from flask import flash
            flash('PDF export requires ReportLab installation', 'warning')
            return redirect(url_for('dashboard.professional_dashboard'))

        # Create professional PDF report
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        # Title
        elements.append(Paragraph("Professional MT5 Trading Journal Report", title_style))
        elements.append(Spacer(1, 12))

        # Date
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 20))

        # Get data for report
        conn = get_db_connection()
        df = pd.read_sql('SELECT * FROM trades WHERE status = "CLOSED"', conn)

        if not df.empty:
            from app.utils.stats import stats_generator
            stats = stats_generator.generate_trading_statistics(df)

            # Summary table
            summary_data = [
                ['Metric', 'Value'],
                ['Total Trades', stats.get('total_trades', 0)],
                ['Net Profit', f"${stats.get('net_profit', 0):.2f}"],
                ['Win Rate', f"{stats.get('win_rate', 0):.1f}%"],
                ['Profit Factor', f"{stats.get('profit_factor', 0):.2f}"],
                ['Avg Trade', f"${stats.get('avg_trade', 0):.2f}"],
                ['Largest Win', f"${stats.get('largest_win', 0):.2f}"],
                ['Largest Loss', f"${stats.get('largest_loss', 0):.2f}"]
            ]

            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(summary_table)

        conn.close()

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        filename = f"professional_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        add_log('ERROR', f'Professional PDF export error: {e}', 'Export')
        from flask import flash
        flash('Error generating PDF report', 'danger')
        from flask import redirect, url_for
        return redirect(url_for('dashboard.professional_dashboard'))