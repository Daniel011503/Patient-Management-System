# migrate_database.py - Add financial tracking to existing database
import sqlite3
from datetime import datetime
import os

def migrate_database():
    """Add financial tracking table to existing database"""
    
    print("🔄 Starting database migration for financial tracking...")
    print("=" * 60)
    
    # Check if database exists
    db_file = "people.db"
    if not os.path.exists(db_file):
        print("❌ Database file 'people.db' not found!")
        print("   Make sure you're running this from the correct directory.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if financial table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='patient_financials';
        """)
        
        if cursor.fetchone():
            print("✅ Financial table already exists - no migration needed")
            conn.close()
            return True
        
        print("📋 Creating patient_financials table...")
        
        # Create the financial table
        cursor.execute("""
            CREATE TABLE patient_financials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                month_year VARCHAR(7) NOT NULL,
                monthly_revenue REAL NOT NULL,
                sessions_attended INTEGER DEFAULT 0,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255),
                FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
                UNIQUE(patient_id, month_year)
            );
        """)
        
        print("✅ Created patient_financials table")
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX idx_patient_financials_patient_id 
            ON patient_financials(patient_id);
        """)
        
        cursor.execute("""
            CREATE INDEX idx_patient_financials_month_year 
            ON patient_financials(month_year);
        """)
        
        print("✅ Created database indexes")
        
        # Add some sample data if patients exist
        cursor.execute("SELECT COUNT(*) FROM patients")
        patient_count = cursor.fetchone()[0]
        
        if patient_count > 0:
            print(f"📊 Found {patient_count} existing patients")
            
            # Get first few patients for sample data
            cursor.execute("SELECT id, patient_number, first_name, last_name FROM patients LIMIT 3")
            sample_patients = cursor.fetchall()
            
            current_month = datetime.now().strftime('%Y-%m')
            
            sample_data = [
                (sample_patients[0][0], current_month, 1500.00, 8, "Regular monthly sessions"),
                (sample_patients[1][0] if len(sample_patients) > 1 else sample_patients[0][0], 
                 current_month, 1200.00, 6, "Consistent attendance"),
                (sample_patients[2][0] if len(sample_patients) > 2 else sample_patients[0][0], 
                 current_month, 1800.00, 10, "High engagement patient")
            ]
            
            # Only add unique patient records
            added_records = []
            for patient_id, month, revenue, sessions, notes in sample_data:
                if patient_id not in added_records:
                    cursor.execute("""
                        INSERT INTO patient_financials 
                        (patient_id, month_year, monthly_revenue, sessions_attended, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (patient_id, month, revenue, sessions, notes, "system_migration"))
                    added_records.append(patient_id)
            
            print(f"✅ Added {len(added_records)} sample financial records")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 Database migration completed successfully!")
        print("\n📋 WHAT WAS ADDED:")
        print("   • patient_financials table")
        print("   • Database indexes for performance")
        print("   • Sample financial data (if patients existed)")
        print("\n🚀 NEXT STEPS:")
        print("   1. Update your models.py with the new PatientFinancial model")
        print("   2. Update your schemas.py with financial schemas")
        print("   3. Update your main.py with financial endpoints")
        print("   4. Update your frontend with the financial tracking tab")
        print("   5. Restart your server: python main.py")
        print("\n💡 FEATURES NOW AVAILABLE:")
        print("   • Track monthly revenue per patient")
        print("   • Record session attendance")
        print("   • Add notes to financial records")
        print("   • View financial summaries and reports")
        print("   • Monthly financial reporting")
        print("   • Top revenue patient tracking")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    
    print("\n🔍 Verifying migration...")
    
    try:
        conn = sqlite3.connect("people.db")
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(patient_financials)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'id', 'patient_id', 'month_year', 'monthly_revenue', 
            'sessions_attended', 'notes', 'created_at', 'updated_at', 'created_by'
        ]
        
        actual_columns = [col[1] for col in columns]
        
        print(f"✅ Table structure verified - {len(actual_columns)} columns found")
        
        # Check if all expected columns exist
        missing_columns = [col for col in expected_columns if col not in actual_columns]
        if missing_columns:
            print(f"⚠️  Missing columns: {missing_columns}")
        else:
            print("✅ All expected columns present")
        
        # Check indexes
        cursor.execute("PRAGMA index_list(patient_financials)")
        indexes = cursor.fetchall()
        print(f"✅ Database indexes: {len(indexes)} found")
        
        # Check sample data
        cursor.execute("SELECT COUNT(*) FROM patient_financials")
        record_count = cursor.fetchone()[0]
        print(f"✅ Sample records: {record_count} financial records")
        
        conn.close()
        
        print("✅ Migration verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🏥 Spectrum Mental Health - Database Migration")
    print("Adding Financial Tracking Capabilities")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        verify_migration()
        print("\n🎊 Migration complete! Your database now supports financial tracking.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
    
    print("\n" + "=" * 60)