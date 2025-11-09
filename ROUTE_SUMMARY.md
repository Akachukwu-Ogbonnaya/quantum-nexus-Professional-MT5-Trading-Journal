# Flask Route Summary

## All Routes

| Route | Function | Methods | File | Line |
|-------|----------|---------|------|------|
| `/` | `index` | GET | app.py | 2102 |
| `/login` | `login` | GET, POST | app.py | 2109 |
| `/register` | `register` | GET, POST | app.py | 2143 |
| `/logout` | `logout` | GET | app.py | 2175 |
| `/dashboard` | `professional_dashboard` | GET | app.py | 2188 |
| `/journal` | `journal` | GET | app.py | 2232 |
| `/trade_plan` | `trade_plan` | GET, POST | app.py | 2447 |
| `/edit_trade_plan/<int:plan_id>` | `edit_trade_plan` | POST | app.py | 2596 |
| `/delete_trade_plan/<int:plan_id>` | `delete_trade_plan` | GET | app.py | 2660 |
| `/account_growth` | `account_growth` | GET | app.py | 2684 |
| `/realtime_logs` | `realtime_logs` | GET | app.py | 2690 |
| `/ai_qa` | `ai_qa` | GET | app.py | 2696 |
| `/notes` | `notes` | GET | app.py | 2702 |
| `/overview` | `overview` | GET | app.py | 2708 |
| `/trade_results/<period>` | `trade_results` | GET | app.py | 2715 |
| `/configuration` | `configuration` | GET, POST | app.py | 2726 |
| `/debug/mt5_connection` | `debug_mt5_connection` | GET | app.py | 2757 |
| `/debug/data_flow_test` | `debug_data_flow_test` | GET | app.py | 2772 |
| `/debug/import_test` | `debug_import_test` | GET | app.py | 2778 |
| `/debug/force_correct_connection` | `debug_force_correct_connection` | GET | app.py | 2784 |
| `/quick/realtime_logs` | `quick_realtime_logs` | GET | app.py | 2799 |
| `/quick/journal` | `quick_journal` | GET | app.py | 2804 |
| `/quick/trade_plan` | `quick_trade_plan` | GET | app.py | 2809 |
| `/api/stats/<period>` | `api_stats` | GET | app.py | 2817 |
| `/api/equity_curve` | `api_equity_curve` | GET | app.py | 2857 |
| `/api/trade_results_data` | `api_trade_results_data` | GET | app.py | 2906 |
| `/api/calendar/<int:year>/<int:month>` | `api_calendar` | GET | app.py | 2942 |
| `/api/calendar_pnl` | `api_calendar_pnl` | GET | app.py | 2953 |
| `/api/logs` | `api_logs` | GET | app.py | 2974 |
| `/api/profit_loss_distribution` | `api_profit_loss_distribution` | GET | app.py | 2980 |
| `/api/sync_now` | `api_sync_now` | GET | app.py | 3007 |
| `/export/csv` | `export_csv` | GET | app.py | 3021 |
| `/export/pdf` | `export_pdf` | GET | app.py | 3057 |
| `/trade_plan` | `trade_plan` | GET, POST | trade_plan_test.py | 236 |
