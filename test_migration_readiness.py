#!/usr/bin/env python3
"""
Pre-Migration Test Script
========================

This script tests your current SQLite setup to ensure migration will work smoothly.
Run this before starting the migration process.

Usage:
    python test_migration_readiness.py
"""

import os
import sys
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sqlite_database():
    """Test SQLite database connectivity and integrity"""
    logger.info("Testing SQLite database...")
    
    if not os.path.exists('people.db'):
        logger.error("SQLite database 'people.db' not found!")
        return False
    
    try:
        conn = sqlite3.connect('people.db')
        cursor = conn.cursor()
        
        # Test basic connectivity
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        logger.info(f"SQLite version: {version}")
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables found: {tables}")
        
        # Test each table
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table '{table}': {count} rows")
            
            # Test table structure
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            logger.info(f"Table '{table}' has {len(columns)} columns")
        
        # Test data integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity == "ok":
            logger.info("✓ Database integrity check passed")
        else:
            logger.error(f"✗ Database integrity check failed: {integrity}")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"SQLite test failed: {e}")
        return False

def test_python_dependencies():
    """Test required Python dependencies"""
    logger.info("Testing Python dependencies...")
    
    required_packages = [
        ('sqlalchemy', 'sqlalchemy'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pydantic', 'pydantic'),
        ('python-jose', 'jose'),
        ('passlib', 'passlib'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            logger.info(f"✓ {package_name} is installed")
        except ImportError:
            logger.error(f"✗ {package_name} is missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.error("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_current_models():
    """Test current SQLAlchemy models"""
    logger.info("Testing SQLAlchemy models...")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import Base, Patient, Service
        
        logger.info("✓ Models imported successfully")
        
        # Check model attributes
        patient_attrs = dir(Patient)
        required_attrs = ['id', 'patient_number', 'first_name', 'last_name']
        
        for attr in required_attrs:
            if attr in patient_attrs:
                logger.info(f"✓ Patient model has '{attr}' attribute")
            else:
                logger.error(f"✗ Patient model missing '{attr}' attribute")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Model test failed: {e}")
        return False

def test_application_startup():
    """Test if the application can start"""
    logger.info("Testing application startup...")
    
    try:
        from main import app
        logger.info("✓ FastAPI app imported successfully")
        return True
        
    except Exception as e:
        logger.error(f"Application startup test failed: {e}")
        return False

def test_disk_space():
    """Test available disk space"""
    logger.info("Testing disk space...")
    
    try:
        import shutil
        free_space = shutil.disk_usage('.').free
        free_gb = free_space / (1024**3)
        
        logger.info(f"Available disk space: {free_gb:.2f} GB")
        
        if free_gb < 1:
            logger.warning("Low disk space! Migration may fail with less than 1GB free")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Disk space test failed: {e}")
        return False

def test_postgresql_requirements():
    """Test PostgreSQL migration requirements"""
    logger.info("Testing PostgreSQL migration requirements...")
    
    # Test if psycopg2 is available (will be installed during migration)
    try:
        import psycopg2
        logger.info("✓ psycopg2 is already installed")
    except ImportError:
        logger.info("ℹ psycopg2 will be installed during migration setup")
    
    # Test if Docker is available (optional)
    try:
        import subprocess
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✓ Docker is available: {result.stdout.strip()}")
        else:
            logger.info("ℹ Docker not available - will use local PostgreSQL")
    except FileNotFoundError:
        logger.info("ℹ Docker not available - will use local PostgreSQL")
    
    return True

def create_migration_report():
    """Create a pre-migration report"""
    logger.info("Creating pre-migration report...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'sqlite_file': 'people.db',
        'file_size': os.path.getsize('people.db') if os.path.exists('people.db') else 0,
        'tables': {},
        'total_rows': 0
    }
    
    try:
        conn = sqlite3.connect('people.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            report['tables'][table] = count
            report['total_rows'] += count
        
        conn.close()
        
        # Save report
        import json
        with open('pre_migration_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Pre-migration report saved: pre_migration_report.json")
        logger.info(f"Total rows to migrate: {report['total_rows']}")
        
    except Exception as e:
        logger.error(f"Failed to create migration report: {e}")

def main():
    """Main test function"""
    logger.info("🔍 Running pre-migration tests...")
    logger.info("=" * 50)
    
    tests = [
        ("SQLite Database", test_sqlite_database),
        ("Python Dependencies", test_python_dependencies),
        ("SQLAlchemy Models", test_current_models),
        ("Application Startup", test_application_startup),
        ("Disk Space", test_disk_space),
        ("PostgreSQL Requirements", test_postgresql_requirements),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Testing: {test_name}")
        logger.info("-" * 30)
        
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    # Create migration report
    create_migration_report()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("✅ Your system is ready for PostgreSQL migration")
        logger.info("📝 Next step: Run 'python setup_postgresql.py --docker'")
    else:
        logger.warning(f"\n⚠️  {failed} test(s) failed")
        logger.warning("❗ Please fix the issues above before starting migration")
        logger.warning("📞 Check the troubleshooting guide if you need help")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
