#!/usr/bin/env python3
"""
Debug script to investigate the time display issue in appointments.
This script connects to PostgreSQL and examines the raw data.
"""

import psycopg2
import sqlite3
from datetime import datetime, date
import sys
import os
import getpass

def connect_to_sqlite():
    """Connect to SQLite database"""
    sqlite_path = "people.db"
    if os.path.exists(sqlite_path):
        try:
            conn = sqlite3.connect(sqlite_path)
            return conn, "sqlite"
        except sqlite3.Error as e:
            print(f"❌ SQLite connection failed: {e}")
    return None, None

def connect_to_postgresql():
    """Connect to PostgreSQL database"""
    try:
        # Use credentials from .env file
        conn = psycopg2.connect(
            host="localhost",
            database="spectrum_db",
            user="postgres",
            password="dannynico011",
            port="5432"
        )
        return conn, "postgresql"
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return None, None

def connect_to_database():
    """Try to connect to available database"""
    print("🔍 Checking available databases...")
    
    # First try SQLite (simpler)
    conn, db_type = connect_to_sqlite()
    if conn:
        print(f"✅ Connected to SQLite database: people.db")
        return conn, db_type
    
    # Then try PostgreSQL
    print("SQLite not found, trying PostgreSQL...")
    conn, db_type = connect_to_postgresql()
    if conn:
        print(f"✅ Connected to PostgreSQL database")
        return conn, db_type
    
    print("❌ Could not connect to any database")
    return None, None

def analyze_time_data():
    """Analyze time data in the services table"""
    conn, db_type = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print(f"🔍 ANALYZING TIME DATA IN SERVICES TABLE ({db_type.upper()})")
        print("=" * 60)
        
        # Get all appointment services with time-related fields
        query = """
        SELECT 
            id,
            patient_id,
            service_type,
            service_date,
            service_time,
            service_category,
            sheet_type,
            created_at
        FROM services 
        WHERE service_category = 'appointment' 
        ORDER BY service_date DESC
        LIMIT 20;
        """
        
        cursor.execute(query)
        services = cursor.fetchall()
        
        print(f"📋 Found {len(services)} appointment services:")
        print()
        
        today = date.today()
        past_count = 0
        future_count = 0
        
        for service in services:
            service_id, patient_id, service_type, service_date, service_time, service_category, sheet_type, created_at = service
            
            # Handle different date formats
            if isinstance(service_date, str):
                try:
                    service_date = datetime.strptime(service_date, '%Y-%m-%d').date()
                except:
                    try:
                        service_date = datetime.strptime(service_date, '%Y-%m-%d %H:%M:%S').date()
                    except:
                        print(f"⚠️  Could not parse date: {service_date}")
                        continue
            
            # Determine if this is past or future
            is_past = service_date < today
            is_future = service_date > today
            is_today = service_date == today
            
            if is_past:
                past_count += 1
                date_status = "📅 PAST"
            elif is_future:
                future_count += 1
                date_status = "📅 FUTURE"
            else:
                date_status = "📅 TODAY"
            
            print(f"🔍 Service ID: {service_id}")
            print(f"   Patient ID: {patient_id}")
            print(f"   Service Type: {service_type}")
            print(f"   Service Date: {service_date} {date_status}")
            print(f"   Service Time: {repr(service_time)} (type: {type(service_time).__name__})")
            print(f"   Category: {service_category}")
            print(f"   Sheet Type: {sheet_type}")
            print(f"   Created: {created_at}")
            
            # Check if service_time is empty/null for past vs future
            if service_time is None or service_time == '':
                print(f"   ⚠️  TIME ISSUE: service_time is {repr(service_time)}")
            else:
                print(f"   ✅ TIME OK: {service_time}")
            
            print()
        
        print("📊 SUMMARY:")
        print(f"   Past appointments: {past_count}")
        print(f"   Future appointments: {future_count}")
        print()
        
        # Check for patterns in time data
        print("🔍 CHECKING TIME DATA PATTERNS:")
        
        # Adjust queries for SQLite vs PostgreSQL
        if db_type == "sqlite":
            current_date_expr = "date('now')"
        else:
            current_date_expr = "CURRENT_DATE"
        
        # Past appointments with missing time
        cursor.execute(f"""
        SELECT COUNT(*) FROM services 
        WHERE service_category = 'appointment' 
        AND service_date < {current_date_expr}
        AND (service_time IS NULL OR service_time = '');
        """)
        past_missing_time = cursor.fetchone()[0]
        
        # Future appointments with time data
        cursor.execute(f"""
        SELECT COUNT(*) FROM services 
        WHERE service_category = 'appointment' 
        AND service_date > {current_date_expr}
        AND service_time IS NOT NULL AND service_time != '';
        """)
        future_with_time = cursor.fetchone()[0]
        
        # Total past and future appointments
        cursor.execute(f"""
        SELECT COUNT(*) FROM services 
        WHERE service_category = 'appointment' 
        AND service_date < {current_date_expr};
        """)
        total_past = cursor.fetchone()[0]
        
        cursor.execute(f"""
        SELECT COUNT(*) FROM services 
        WHERE service_category = 'appointment' 
        AND service_date > {current_date_expr};
        """)
        total_future = cursor.fetchone()[0]
        
        print(f"   Past appointments missing time: {past_missing_time}/{total_past}")
        print(f"   Future appointments with time: {future_with_time}/{total_future}")
        
        if past_missing_time > 0 and future_with_time > 0:
            print("   🎯 ISSUE CONFIRMED: Past appointments missing time data!")
            
            # Show a few examples of each
            print("\n🔍 EXAMPLES OF PROBLEMATIC PAST APPOINTMENTS:")
            cursor.execute(f"""
            SELECT id, service_date, service_time, service_type 
            FROM services 
            WHERE service_category = 'appointment' 
            AND service_date < {current_date_expr}
            AND (service_time IS NULL OR service_time = '')
            LIMIT 5;
            """)
            
            for row in cursor.fetchall():
                print(f"   ID {row[0]}: {row[1]} - {row[3]} - time: {repr(row[2])}")
            
            print("\n🔍 EXAMPLES OF WORKING FUTURE APPOINTMENTS:")
            cursor.execute(f"""
            SELECT id, service_date, service_time, service_type 
            FROM services 
            WHERE service_category = 'appointment' 
            AND service_date > {current_date_expr}
            AND service_time IS NOT NULL AND service_time != ''
            LIMIT 5;
            """)
            
            for row in cursor.fetchall():
                print(f"   ID {row[0]}: {row[1]} - {row[3]} - time: {repr(row[2])}")
                
        print("\n💡 PROPOSED SOLUTION:")
        print("   We can update past appointments to have default time values")
        print("   or extract time from service_date if it contains datetime info.")
        
        return db_type  # Return database type for use in fix function
        
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def fix_missing_times(db_type):
    """Fix missing time data for past appointments"""
    conn, _ = connect_to_database()
    if not conn:
        return
    
    response = input("\n🔧 Do you want to fix missing time data? (y/N): ")
    if response.lower() != 'y':
        print("ℹ️  Skipping fix.")
        conn.close()
        return
    
    try:
        cursor = conn.cursor()
        
        # Update past appointments with missing time to have a default time
        default_time = input("Enter default time for past appointments (e.g., '10:00'): ")
        if not default_time:
            default_time = "10:00"
        
        # Adjust query for SQLite vs PostgreSQL
        if db_type == "sqlite":
            current_date_expr = "date('now')"
        else:
            current_date_expr = "CURRENT_DATE"
        
        cursor.execute(f"""
        UPDATE services 
        SET service_time = ?
        WHERE service_category = 'appointment' 
        AND service_date < {current_date_expr}
        AND (service_time IS NULL OR service_time = '');
        """ if db_type == "sqlite" else f"""
        UPDATE services 
        SET service_time = %s
        WHERE service_category = 'appointment' 
        AND service_date < {current_date_expr}
        AND (service_time IS NULL OR service_time = '');
        """, (default_time,))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ Updated {affected_rows} past appointments with default time '{default_time}'")
        
    except Exception as e:
        print(f"❌ Failed to fix time data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🏥 Spectrum Mental Health - Time Data Debug Tool")
    print("=" * 50)
    
    # First, analyze the data
    db_type = analyze_time_data()
    
    # Optionally fix the issue
    if db_type:
        fix_missing_times(db_type)
    
    print("\n✅ Debug complete!")
