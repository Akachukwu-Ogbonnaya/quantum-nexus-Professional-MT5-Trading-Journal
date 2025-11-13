Professional MT5 Trading Journal
<div align="center">
https://img.shields.io/badge/version-2.0.0-blue.svg
https://img.shields.io/badge/python-3.8+-green.svg
https://img.shields.io/badge/flask-2.3+-lightgrey.svg
https://img.shields.io/badge/metatrader-5-compatible-orange.svg

Advanced Trading Analytics Platform with Universal MT5 Integration

Features • Installation • Usage • Configuration • API

</div>
🌟 Overview
The Professional MT5 Trading Journal is a comprehensive, enterprise-grade trading analytics platform designed for serious traders. It provides universal adaptability to any MT5 account, advanced trading analytics, real-time synchronization, and professional UI/UX design.

Built with Flask and featuring a modern web interface, this application transforms raw MT5 trading data into actionable insights through sophisticated analytics, risk management tools, and performance tracking.

🚀 Key Features
📊 Advanced Analytics & Dashboard
Executive Dashboard: Comprehensive overview of trading performance

Real-time Statistics: Win rate, profit factor, Sharpe ratio, and more

Performance Metrics: Daily, weekly, monthly, and custom period analysis

Equity Curve Tracking: Visualize account growth and drawdowns

🔄 Universal MT5 Integration
Automatic Detection: Seamlessly connects to any MT5 account

Real-time Synchronization: Live trade updates and position tracking

Demo Mode: Full functionality without MT5 connection

Universal Configuration: Adapts to any broker and account type

📈 Professional Risk Management
Risk Analysis Dashboard: Comprehensive risk metrics and scoring

Drawdown Analysis: Maximum and current drawdown monitoring

Position Sizing: Advanced risk-based position calculations

Risk Recommendations: AI-powered risk management suggestions

📅 Calendar & Performance Tracking
Daily P&L Calendar: Visual monthly performance tracking

Trade Journal: Detailed trade analysis and note-taking

Performance Trends: Identify patterns and improvement areas

Goal Tracking: Set and monitor trading objectives

🧠 AI-Powered Insights
Quantum AI Q&A: Intelligent trading analysis and recommendations

Psychology Analysis: Mood tracking and emotional state monitoring

Market Analysis: Context-aware market insights

Coach Advice: Personalized trading improvement suggestions

🛠️ Advanced Features
Trade Planning: Pre-trade analysis and strategy planning

Psychology Log: Track emotional state and trading mindset

Export Capabilities: CSV and PDF reporting

Real-time WebSocket: Live updates and notifications

Multi-user Support: Secure user authentication system

🛠 Installation
Prerequisites
Python 3.8 or higher

MetaTrader 5 (optional - runs in demo mode without MT5)

Modern web browser

Quick Start
Clone or Download the Application

bash
git clone <repository-url>
cd mt5-trading-journal
Install Python Dependencies

bash
pip install -r requirements.txt
Initialize the Application

bash
python app.py
The application will automatically:

Create necessary directory structure

Initialize the database with advanced schema

Generate default configuration

Start the web server

Access the Application

text
Open your browser and navigate to: http://127.0.0.1:5000
Default Login
Username: Any username (auto-created)

Password: Any password (auto-created)

⚙️ Configuration
Automatic Configuration
The application automatically creates a config.json file with universal defaults:

json
{
  "mt5": {
    "terminal_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "account": 0,
    "password": "",
    "server": ""
  },
  "web_app": {
    "secret_key": "auto-generated",
    "host": "127.0.0.1",
    "port": 5000,
    "debug": false
  },
  "sync": {
    "auto_sync_interval": 300,
    "days_history": 90,
    "real_time_updates": true
  }
}
MT5 Connection Setup
Navigate to Configuration Page

Access via the sidebar menu

Enter your MT5 account details:

Server name

Account number

Password

Terminal path (optional)

Test Connection

Use the built-in connection tester

Automatic fallback to demo mode if connection fails

Auto-Sync Settings

Configure synchronization interval (default: 5 minutes)

Set days of history to import

Enable real-time updates

📖 Usage Guide
Dashboard
Real-time Overview: Account balance, equity, margin, and open positions

Performance Metrics: Key statistics and performance indicators

Calendar View: Monthly P&L tracking with daily breakdowns

Quick Actions: Fast access to key features

Trade Journal
Complete Trade History: All trades with detailed metrics

Advanced Filtering: Filter by symbol, status, date range

Trade Analysis: Risk-reward ratios, duration, and performance metrics

Notes & Comments: Add insights and lessons learned

Risk Analysis
Risk Scoring: Overall risk assessment (0-100 scale)

Drawdown Analysis: Visualize equity curve and drawdown periods

Concentration Risk: Identify overexposure to specific symbols

Recommendations: Actionable risk management advice

Trade Planning
Pre-trade Analysis: Plan trades with entry/exit conditions

Strategy Definition: Define trading strategies and setups

Risk Parameters: Set stop-loss, take-profit, and position size

Outcome Tracking: Record actual vs planned results

AI Q&A System
Ask Questions: Natural language queries about your trading

Performance Analysis: Get insights on win rate, patterns, and improvements

Market Context: Analysis based on current market conditions

Psychology Support: Emotional state analysis and recommendations

🔧 API Endpoints
The application provides RESTful API endpoints for advanced integration:

Data Synchronization
GET /api/sync_now - Manual synchronization trigger

GET /api/sync_status - Current synchronization status

Analytics & Statistics
GET /api/stats/<period> - Trading statistics for specified period

GET /api/equity_curve - Equity curve data for charts

GET /api/trade_results_data - Trade results with filtering

GET /api/calendar/<year>/<month> - Calendar P&L data

Export & Reporting
GET /export/csv - Export trades to CSV

GET /export/pdf - Generate PDF report (requires ReportLab)

AI & Advanced Features
POST /api/ai/coach_advice - AI trading coach recommendations

POST /api/ai/risk_assessment - AI-powered risk analysis

POST /api/ai/market_analysis - Context-aware market analysis

🗂 Database Schema
The application uses SQLite with an advanced schema including:

Core Tables
trades: Complete trade history with 30+ metrics

users: User authentication and preferences

account_history: Equity curve and balance tracking

calendar_pnl: Daily performance metrics

trade_plans: Pre-trade planning and analysis

psychology_logs: Emotional state and mindset tracking

Advanced Indexing
Optimized indexes for performance

Automatic database backups

Data integrity constraints

🎯 Advanced Features
Universal MT5 Adaptability
Auto-detection: Works with any MT5 broker

Flexible Configuration: No hard-coded broker settings

Error Handling: Graceful fallback to demo mode

Reconnection Logic: Automatic recovery from disconnections

Real-time Processing
WebSocket Integration: Live data updates

Background Synchronization: Non-blocking data imports

Auto-backup: Scheduled database backups

Performance Optimization: Efficient data processing

Professional Calculations
Risk-Reward Analysis: Advanced R:R ratio calculations

Position Sizing: Kelly Criterion and risk-based sizing

Performance Metrics: Sharpe ratio, recovery factor, expectancy

Statistical Analysis: Win streaks, consistency scoring

🔒 Security Features
User Authentication: Secure login system

Password Hashing: Bcrypt password protection

CSRF Protection: Form security

Session Management: Secure session handling

Input Validation: Comprehensive data validation

🐛 Troubleshooting
Common Issues
MT5 Connection Failed

Verify MT5 is installed and running

Check account credentials in configuration

Ensure firewall allows MT5 connections

Database Errors

Application automatically creates backup and recovery

Check write permissions in application directory

Performance Issues

Reduce synchronization interval

Limit historical data import days

Check system resources

Demo Mode
The application runs fully functional in demo mode when:

MT5 is not installed

Connection credentials are invalid

MT5 is not running

Demo mode provides sample data with realistic trading patterns.

📊 System Requirements
Minimum
Python 3.8+

2GB RAM

100MB disk space

Modern web browser

Recommended
Python 3.10+

4GB RAM

500MB disk space (for extensive trade history)

MT5 installation for live trading

🚀 Deployment
Development
bash
python app.py
Production Considerations
Set debug: false in configuration

Use production web server (Gunicorn, uWSGI)

Configure reverse proxy (Nginx, Apache)

Enable HTTPS

Regular database backups

Monitor system resources

📈 Performance Optimization
Database Optimization
Automatic indexing on key columns

Query optimization for large datasets

Regular vacuum and maintenance

Memory Management
Efficient data caching

Background processing

Automatic log rotation

🤝 Contributing
We welcome contributions to enhance the Professional MT5 Trading Journal:

Fork the repository

Create a feature branch

Implement improvements

Add tests where applicable

Submit a pull request

Areas for Contribution
Additional analytics and metrics

Enhanced visualization

New export formats

Integration with additional platforms

Performance optimizations

📄 License
This project is licensed for personal and commercial use. Please refer to the LICENSE file for detailed terms and conditions.

🆘 Support
For technical support and documentation:

Check the built-in help system

Review configuration examples

Use the debug tools in the application

<div align="center">
Professional MT5 Trading Journal v2.0
Transforming Trading Data into Trading Intelligence

</div>
