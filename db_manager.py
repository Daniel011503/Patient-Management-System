#!/usr/bin/env python3
"""
Database Management Utility
===========================

This script provides various database management operations for the Spectrum application.

Usage:
    python db_manager.py [command] [options]

Commands:
    backup      - Create a backup of the current database
    restore     - Restore from a backup
    migrate     - Run database migrations
    reset       - Reset database (WARNING: destroys all data)
    status      - Show database status and connection info
    shell       - Open database shell
    export      - Export data to CSV/JSON
    import      - Import data from CSV/JSON

Examples:
    python db_manager.py status
    python db_manager.py backup --name manual_backup
    python db_manager.py migrate --target postgresql
"""

import os
import sys
import argparse
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from environment"""
    load_dotenv('.env.development')
    
    return {
        'database_type': os.getenv('DATABASE_TYPE', 'sqlite'),
        'postgres_user': os.getenv('POSTGRES_USER', 'spectrum_user'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD', ''),
        'postgres_host': os.getenv('POSTGRES_HOST', 'localhost'),
        'postgres_port': os.getenv('POSTGRES_PORT', '5432'),
        'postgres_db': os.getenv('POSTGRES_DB', 'spectrum_db'),
    }

def get_database_url(config):
    """Get database URL based on configuration"""
    if config['database_type'] == 'postgresql':
        return f"postgresql://{config['postgres_user']}:{config['postgres_password']}@{config['postgres_host']}:{config['postgres_port']}/{config['postgres_db']}"
    else:
        return "sqlite:///./people.db"

def backup_database(args):
    """Create database backup"""
    config = load_config()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if args.name:
        backup_name = f"{args.name}_{timestamp}"
    else:
        backup_name = f"backup_{timestamp}"
    
    if config['database_type'] == 'postgresql':
        backup_postgresql(config, backup_name)
    else:
        backup_sqlite(backup_name)

def backup_postgresql(config, backup_name):
    """Backup PostgreSQL database"""
    import subprocess
    
    backup_file = f"{backup_name}.sql"
    
    env = os.environ.copy()
    env['PGPASSWORD'] = config['postgres_password']
    
    cmd = [
        'pg_dump',
        '-h', config['postgres_host'],
        '-p', config['postgres_port'],
        '-U', config['postgres_user'],
        '-d', config['postgres_db'],
        '-f', backup_file,
        '--verbose',
        '--no-password'
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        logger.info(f"PostgreSQL backup created: {backup_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e}")
    except FileNotFoundError:
        logger.error("pg_dump not found. Please install PostgreSQL client tools")

def backup_sqlite(backup_name):
    """Backup SQLite database"""
    import shutil
    
    if not os.path.exists('people.db'):
        logger.error("SQLite database 'people.db' not found")
        return
    
    backup_file = f"{backup_name}.db"
    
    try:
        shutil.copy2('people.db', backup_file)
        logger.info(f"SQLite backup created: {backup_file}")
    except Exception as e:
        logger.error(f"Backup failed: {e}")

def show_status(args):
    """Show database status"""
    config = load_config()
    
    print("\n=== Database Status ===")
    print(f"Database Type: {config['database_type']}")
    print(f"Database URL: {get_database_url(config)}")
    
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(get_database_url(config))
        
        with engine.connect() as conn:
            if config['database_type'] == 'postgresql':
                # PostgreSQL status
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"PostgreSQL Version: {version.split(',')[0]}")
                
                result = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
                table_count = result.fetchone()[0]
                print(f"Tables: {table_count}")
                
                result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
                db_size = result.fetchone()[0]
                print(f"Database Size: {db_size}")
                
            else:
                # SQLite status
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.fetchone()[0]
                print(f"SQLite Version: {version}")
                
                result = conn.execute(text("SELECT count(*) FROM sqlite_master WHERE type='table'"))
                table_count = result.fetchone()[0]
                print(f"Tables: {table_count}")
                
                if os.path.exists('people.db'):
                    size = os.path.getsize('people.db')
                    print(f"Database Size: {size:,} bytes")
        
        print("Connection: ✓ Healthy")
        
    except Exception as e:
        print(f"Connection: ✗ Failed - {e}")

def run_migrations(args):
    """Run database migrations"""
    config = load_config()
    
    if args.target == 'postgresql' and config['database_type'] == 'sqlite':
        logger.info("Starting SQLite to PostgreSQL migration...")
        
        # Import and run migration script
        try:
            from migrate_sqlite_to_postgres import main as migrate_main
            success = migrate_main()
            
            if success:
                logger.info("Migration completed successfully!")
                logger.info("Update your .env file to set DATABASE_TYPE=postgresql")
            else:
                logger.error("Migration failed!")
                
        except ImportError:
            logger.error("Migration script not found: migrate_sqlite_to_postgres.py")
        except Exception as e:
            logger.error(f"Migration error: {e}")
    
    elif config['database_type'] == 'postgresql':
        # Run Alembic migrations
        import subprocess
        
        try:
            subprocess.run(['alembic', 'upgrade', 'head'], check=True)
            logger.info("Alembic migrations completed")
        except subprocess.CalledProcessError as e:
            logger.error(f"Alembic migration failed: {e}")
        except FileNotFoundError:
            logger.error("Alembic not found. Install with: pip install alembic")
    
    else:
        logger.error(f"Migration from {config['database_type']} to {args.target} not supported")

def export_data(args):
    """Export data to CSV/JSON"""
    config = load_config()
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(get_database_url(config))
        
        # Get list of tables
        with engine.connect() as conn:
            if config['database_type'] == 'postgresql':
                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            else:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            
            tables = [row[0] for row in result.fetchall()]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = f"export_{timestamp}"
        os.makedirs(export_dir, exist_ok=True)
        
        for table in tables:
            if table.startswith('alembic_'):
                continue
                
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                columns = result.keys()
                
                if args.format == 'csv':
                    export_csv(export_dir, table, columns, rows)
                else:
                    export_json(export_dir, table, columns, rows)
        
        logger.info(f"Data exported to {export_dir}/")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")

def export_csv(export_dir, table, columns, rows):
    """Export table data to CSV"""
    filename = os.path.join(export_dir, f"{table}.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        writer.writerows(rows)

def export_json(export_dir, table, columns, rows):
    """Export table data to JSON"""
    filename = os.path.join(export_dir, f"{table}.json")
    
    data = []
    for row in rows:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Handle datetime objects
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            row_dict[col] = value
        data.append(row_dict)
    
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, default=str)

def reset_database(args):
    """Reset database (WARNING: destroys all data)"""
    if not args.confirm:
        print("WARNING: This will destroy ALL data in the database!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm != 'YES':
            logger.info("Reset cancelled")
            return
    
    config = load_config()
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(get_database_url(config))
        
        # Import models
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import Base
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        logger.info("All tables recreated")
        
        logger.info("Database reset completed")
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Database management utility for Spectrum")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--name', help='Backup name prefix')
    
    # Status command
    subparsers.add_parser('status', help='Show database status')
    
    # Migration command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
    migrate_parser.add_argument('--target', choices=['postgresql'], default='postgresql',
                               help='Target database type')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='json',
                              help='Export format')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset database (WARNING: destroys data)')
    reset_parser.add_argument('--confirm', action='store_true',
                             help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'backup':
        backup_database(args)
    elif args.command == 'status':
        show_status(args)
    elif args.command == 'migrate':
        run_migrations(args)
    elif args.command == 'export':
        export_data(args)
    elif args.command == 'reset':
        reset_database(args)

if __name__ == "__main__":
    main()
