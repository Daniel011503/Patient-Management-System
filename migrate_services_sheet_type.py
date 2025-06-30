# migrate_services_sheet_type.py
# Adds 'sheet_type' column to the 'services' table for attendance/appointment sheet tracking
import sqlite3

DB_FILE = 'people.db'

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Check if sheet_type column already exists
    cursor.execute("PRAGMA table_info(services);")
    columns = [row[1] for row in cursor.fetchall()]
    if 'sheet_type' in columns:
        print('✅ sheet_type column already exists in services table.')
        conn.close()
        return
    print('🔄 Adding sheet_type column to services table...')
    cursor.execute("ALTER TABLE services ADD COLUMN sheet_type TEXT NOT NULL DEFAULT 'attendance';")
    conn.commit()
    print('✅ Migration complete: sheet_type column added.')
    conn.close()

if __name__ == '__main__':
    migrate()
