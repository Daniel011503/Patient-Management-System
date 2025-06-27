# fix_database.py - Run this to fix the database schema issue

import os
import shutil
from datetime import datetime

def backup_and_recreate_database():
    """Backup existing database and create a fresh one"""
    
    db_file = "people.db"
    
    print("🔧 Fixing database schema issue...")
    print("=" * 50)
    
    # Create backup if database exists
    if os.path.exists(db_file):
        backup_name = f"people_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_file, backup_name)
        print(f"✅ Created backup: {backup_name}")
        
        # Remove the problematic database
        os.remove(db_file)
        print(f"✅ Removed old database: {db_file}")
    else:
        print("ℹ️ No existing database found")
    
    print("\n🚀 Next steps:")
    print("1. Run your application: python main.py")
    print("2. The database will be recreated automatically")
    print("3. You'll need to recreate the admin user")
    print("4. Add your patients again (sorry!)")
    
    print("\n⚠️ What this fixes:")
    print("• Removes the problematic 'sheet_type' column")
    print("• Creates fresh tables matching your current models")
    print("• Eliminates the NOT NULL constraint error")

if __name__ == "__main__":
    backup_and_recreate_database()