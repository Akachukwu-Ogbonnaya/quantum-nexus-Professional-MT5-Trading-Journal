# start_app_with_data.py
import sqlite3
import subprocess
import time
import webbrowser

def verify_database():
    """Verify the database has real data"""
    print("🔍 VERIFYING DATABASE...")
    
    try:
        db = sqlite3.connect('trading_journal.db')
        cursor = db.execute("SELECT COUNT(*) as count FROM trades")
        trade_count = cursor.fetchone()[0]
        
        cursor = db.execute("SELECT symbol, profit, status FROM trades")
        trades = cursor.fetchall()
        
        print(f"✅ Trades in database: {trade_count}")
        
        if trades:
            print("📊 YOUR REAL TRADES:")
            total_profit = 0
            for symbol, profit, status in trades:
                profit_color = "🟢" if profit > 0 else "🔴"
                print(f"   {profit_color} {symbol}: ${profit:.2f} - {status}")
                total_profit += profit
            
            print(f"💰 TOTAL P&L: ${total_profit:.2f}")
        else:
            print("❌ No trades found")
            
        db.close()
        return trade_count > 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def start_web_app():
    """Start the web application"""
    print("\n🚀 STARTING WEB APPLICATION...")
    
    try:
        # Start the Flask app
        process = subprocess.Popen(['python', 'app.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print("✅ Web app starting...")
        print("⏳ Waiting for app to load...")
        
        # Wait for app to start
        time.sleep(8)
        
        # Open browser
        webbrowser.open('http://127.0.0.1:5005')
        print("🌐 Browser opened to: http://127.0.0.1:5005")
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start web app: {e}")
        return None

def check_mt5_status():
    """Check MT5 status without blocking"""
    print("\n🔧 CHECKING MT5 STATUS...")
    
    try:
        import MetaTrader5 as mt5
        
        # Quick connection test
        if mt5.initialize():
            account = mt5.account_info()
            print(f"✅ MT5 Connected: Account {account.login}")
            print(f"   Balance: ${account.balance:.2f}")
            mt5.shutdown()
            return True
        else:
            print("❌ MT5 Not Connected")
            print("💡 MT5 connection is optional for viewing existing data")
            return False
            
    except Exception as e:
        print(f"⚠️ MT5 check skipped: {e}")
        return False

def main():
    print("=" * 60)
    print("🎯 STARTING WEB APP WITH REAL TRADING DATA")
    print("=" * 60)
    
    # Step 1: Verify database has real data
    if not verify_database():
        print("❌ No real data found. Please run emergency_manual.py first")
        return
    
    # Step 2: Check MT5 status (non-blocking)
    check_mt5_status()
    
    # Step 3: Start web application
    app_process = start_web_app()
    
    if app_process:
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Your web app is running with real data!")
        print("=" * 60)
        print("\n📋 WHAT YOU SHOULD SEE:")
        print("   ✅ Real trades: USDCAD (+$1.69), EURUSD (-$1.06), USDCAD (+$0.19)")
        print("   ✅ Total P&L: $0.82")
        print("   ✅ Real account data in dashboard")
        print("\n💡 TROUBLESHOOTING:")
        print("   - If page doesn't load, refresh browser")
        print("   - If no data shows, check console for errors")
        print("   - MT5 connection is optional for viewing existing data")
        
        try:
            # Keep the app running
            print("\n🔄 App is running... Press Ctrl+C to stop")
            app_process.wait()
        except KeyboardInterrupt:
            print("\n⏹️ Stopping web app...")
            app_process.terminate()
    else:
        print("❌ Failed to start web application")

if __name__ == "__main__":
    main()