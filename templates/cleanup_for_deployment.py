#!/usr/bin/env python3
"""
Project Cleaner for PythonAnywhere Deployment
Cleans unnecessary files to save space for free tier hosting
"""

import os
import shutil
import glob
from pathlib import Path

def clean_project():
    """Clean project files for deployment"""
    print("🧹 Starting project cleanup for PythonAnywhere deployment...")
    
    # Files and folders to remove
    items_to_remove = [
        # Session files
        "flask_session",
        
        # Cache files
        "__pycache__",
        
        # Logs (will regenerate)
        "logs",
        
        # Temporary exports
        "exports",
        
        # Backup databases (keep only latest)
        "database/backups",
        
        # Redundant static folders
        "static/csss",
        "static/jss",
        
        # Backup template files
        "templates/statistics/risk_analysis.html.backup",
        "templates/statistics/trend_analysis.html.backup",
        
        # Test and temporary files
        "test.txt",
    ]
    
    # File patterns to remove
    patterns_to_remove = [
        "*.pyc",           # Python cache files
        "*.log",           # Log files
        "flask_session/*", # Session files
    ]
    
    # Keep only essential files
    essential_files = [
        "app.py",
        "requirements.txt", 
        "config.json",
        "start_app_with_data.py",
        "project_analyzer.py",
        "route_template_checker.py",
        "scan_templates_in_app.py",
        "ROUTE_SUMMARY.md",
        "database/trades.db",  # Keep main database
        "static/css/style.css",
        "static/js/dashboard.js",
        "templates/",
    ]
    
    total_freed = 0
    removed_count = 0
    
    print("\n📁 Cleaning folders...")
    for item in items_to_remove:
        if os.path.exists(item):
            if os.path.isdir(item):
                size = get_folder_size(item)
                shutil.rmtree(item)
                print(f"   ✅ Removed folder: {item} ({size:.2f} MB)")
                total_freed += size
                removed_count += 1
            else:
                size = os.path.getsize(item) / (1024 * 1024)
                os.remove(item)
                print(f"   ✅ Removed file: {item} ({size:.2f} MB)")
                total_freed += size
                removed_count += 1
    
    print("\n🔍 Cleaning file patterns...")
    for pattern in patterns_to_remove:
        for file_path in glob.glob(pattern, recursive=True):
            if os.path.exists(file_path):
                size = os.path.getsize(file_path) / (1024 * 1024) if os.path.isfile(file_path) else 0
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                print(f"   ✅ Removed: {file_path} ({size:.2f} MB)")
                total_freed += size
                removed_count += 1
    
    # Create fresh logs directory
    print("\n📝 Recreating essential directories...")
    essential_dirs = ["logs", "exports", "database/backups"]
    for dir_path in essential_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"   ✅ Created: {dir_path}")
    
    # Create empty log file
    with open("logs/app.log", "w") as f:
        f.write("# Application Log - Cleaned for deployment\n")
    
    print(f"\n🎉 Cleanup completed!")
    print(f"   📊 Files/Folders removed: {removed_count}")
    print(f"   💾 Space freed: {total_freed:.2f} MB")
    print(f"   📁 Current project size: {get_folder_size('.'):.2f} MB")
    
    # Show remaining project structure
    print(f"\n📂 Final project structure:")
    show_project_tree()

def get_folder_size(folder_path):
    """Calculate folder size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
    return total_size / (1024 * 1024)  # Convert to MB

def show_project_tree(max_depth=3):
    """Display project tree structure"""
    def print_tree(path, prefix="", depth=0):
        if depth > max_depth:
            return
            
        if os.path.isdir(path):
            items = sorted(os.listdir(path))
            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1
                
                if depth == 0:
                    print(f"   {item}/")
                else:
                    connector = "└── " if is_last else "├── "
                    print(f"   {prefix}{connector}{item}/" if os.path.isdir(item_path) else f"   {prefix}{connector}{item}")
                
                if os.path.isdir(item_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    print_tree(item_path, new_prefix, depth + 1)
    
    print_tree(".")

def create_clean_requirements():
    """Create a clean requirements.txt for deployment"""
    requirements = """Flask==2.3.3
flask-socketio==5.3.6
python-socketio==5.8.0
eventlet==0.33.3
pandas==2.0.3
numpy==1.24.3
MetaTrader5==5.0.43
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    print(f"\n📋 Created clean requirements.txt")

def backup_database():
    """Create a backup of the database before cleanup"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "pre_cleanup_backup"
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists("database/trades.db"):
        shutil.copy2("database/trades.db", f"{backup_dir}/trades_backup_{timestamp}.db")
        print(f"💾 Database backed up to: {backup_dir}/trades_backup_{timestamp}.db")

if __name__ == "__main__":
    print("🚀 Quantum Nexus MT5 Journal - Deployment Cleaner")
    print("=" * 50)
    
    # Show initial size
    initial_size = get_folder_size('.')
    print(f"📦 Initial project size: {initial_size:.2f} MB")
    
    # Create backup
    backup_database()
    
    # Ask for confirmation
    response = input("\n❓ Proceed with cleanup? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Cleanup cancelled.")
        exit()
    
    # Perform cleanup
    clean_project()
    
    # Create clean requirements
    create_clean_requirements()
    
    print(f"\n✅ Project is ready for PythonAnywhere deployment!")
    print(f"📤 You can now zip the project and upload to PythonAnywhere")