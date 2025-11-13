# app/utils/installer.py
import os
import platform
import subprocess
import sys
from .system_info import detect_environment

def setup_desktop_environment():
    """Setup desktop-specific environment"""
    if detect_environment() == 'sqlite':
        # Create necessary desktop directories
        desktop_dirs = [
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'exports'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'backups'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'MT5Journal', 'reports')
        ]
        
        for directory in desktop_dirs:
            os.makedirs(directory, exist_ok=True)
        
        # Set desktop-specific configurations
        config.setdefault('desktop', {})
        config['desktop'].update({
            'auto_start': False,
            'minimize_to_tray': True,
            'start_with_windows': False,
            'export_directory': desktop_dirs[0],
            'backup_directory': desktop_dirs[1]
        })
        
        print("✅ Desktop environment configured")

def setup_auto_start():
    """Setup auto-start based on platform"""
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            setup_windows_auto_start()
        elif system == 'darwin':
            setup_macos_auto_start()
        elif system == 'linux':
            setup_linux_auto_start()
    except Exception as e:
        print(f'Auto-start setup failed: {e}')

def setup_windows_auto_start():
    """Setup Windows auto-start"""
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
            app_path = os.path.abspath(sys.executable)
            winreg.SetValueEx(reg_key, "MT5Journal", 0, winreg.REG_SZ, app_path)
            
        print('Windows auto-start configured')
    except Exception as e:
        print(f'Windows auto-start failed: {e}')

def setup_macos_auto_start():
    """Setup macOS auto-start"""
    try:
        launch_agents_dir = os.path.expanduser('~/Library/LaunchAgents')
        os.makedirs(launch_agents_dir, exist_ok=True)
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mt5journal.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>app</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
        
        plist_path = os.path.join(launch_agents_dir, 'com.mt5journal.app.plist')
        with open(plist_path, 'w') as f:
            f.write(plist_content)
            
        print('macOS auto-start configured')
    except Exception as e:
        print(f'macOS auto-start failed: {e}')

def setup_linux_auto_start():
    """Setup Linux auto-start"""
    try:
        autostart_dir = os.path.expanduser('~/.config/autostart')
        os.makedirs(autostart_dir, exist_ok=True)
        
        desktop_content = f'''[Desktop Entry]
Type=Application
Version=1.0
Name=MT5 Journal
Comment=Professional MT5 Trading Journal
Exec={sys.executable} -m app
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true'''
        
        desktop_path = os.path.join(autostart_dir, 'mt5-journal.desktop')
        with open(desktop_path, 'w') as f:
            f.write(desktop_content)
            
        print('Linux auto-start configured')
    except Exception as e:
        print(f'Linux auto-start failed: {e}')