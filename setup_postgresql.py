#!/usr/bin/env python3
"""
PostgreSQL Setup and Testing Script
==================================

This script helps you set up PostgreSQL for your application and test the connection.
Run this before attempting the migration.

Usage:
    python setup_postgresql.py

Options:
    --docker    : Set up PostgreSQL using Docker
    --local     : Use local PostgreSQL installation
    --test      : Test connection to existing PostgreSQL setup
"""

import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_docker_postgresql():
    """Set up PostgreSQL using Docker"""
    logger.info("Setting up PostgreSQL with Docker...")
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        logger.info("Docker is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Docker is not installed or not in PATH")
        return False
    
    # Stop and remove existing container if it exists
    try:
        subprocess.run(["docker", "stop", "spectrum-postgres"], capture_output=True)
        subprocess.run(["docker", "rm", "spectrum-postgres"], capture_output=True)
        logger.info("Removed existing PostgreSQL container")
    except:
        pass
    
    # Start new PostgreSQL container
    docker_cmd = [
        "docker", "run", "--name", "spectrum-postgres",
        "-e", "POSTGRES_DB=spectrum_db",
        "-e", "POSTGRES_USER=spectrum_user",
        "-e", "POSTGRES_PASSWORD=secure_password_123",
        "-p", "5432:5432",
        "-d", "postgres:14"
    ]
    
    try:
        result = subprocess.run(docker_cmd, check=True, capture_output=True, text=True)
        logger.info("PostgreSQL container started successfully")
        logger.info("Container ID: " + result.stdout.strip())
        
        # Wait for PostgreSQL to be ready
        import time
        logger.info("Waiting for PostgreSQL to be ready...")
        time.sleep(10)
        
        # Test connection
        if test_postgresql_connection():
            logger.info("PostgreSQL setup completed successfully!")
            logger.info("Connection details:")
            logger.info("  Host: localhost")
            logger.info("  Port: 5432")
            logger.info("  Database: spectrum_db")
            logger.info("  User: spectrum_user")
            logger.info("  Password: secure_password_123")
            return True
        else:
            logger.error("PostgreSQL container started but connection failed")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start PostgreSQL container: {e}")
        return False

def setup_local_postgresql():
    """Guide for setting up local PostgreSQL"""
    logger.info("Setting up local PostgreSQL...")
    
    print("\nTo set up PostgreSQL locally:")
    print("1. Download and install PostgreSQL from: https://www.postgresql.org/download/")
    print("2. During installation, remember the password you set for the 'postgres' user")
    print("3. After installation, open pgAdmin or use psql to create:")
    print("   - A database named 'spectrum_db'")
    print("   - A user named 'spectrum_user' with password 'secure_password_123'")
    print("   - Grant all privileges on 'spectrum_db' to 'spectrum_user'")
    print("\nSQL commands to run:")
    print("  CREATE DATABASE spectrum_db;")
    print("  CREATE USER spectrum_user WITH PASSWORD 'secure_password_123';")
    print("  GRANT ALL PRIVILEGES ON DATABASE spectrum_db TO spectrum_user;")
    print("  ALTER USER spectrum_user CREATEDB;")
    
    input("\nPress Enter when you've completed the above steps...")
    
    return test_postgresql_connection()

def test_postgresql_connection():
    """Test PostgreSQL connection"""
    logger.info("Testing PostgreSQL connection...")
    
    try:
        from sqlalchemy import create_engine, text
        
        database_url = "postgresql://spectrum_user:secure_password_123@localhost:5432/spectrum_db"
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
            return True
            
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        logger.error("Please check your PostgreSQL installation and credentials")
        return False

def create_env_file():
    """Create .env.development file with PostgreSQL settings"""
    env_content = """# Development Environment Configuration for PostgreSQL Migration
DATABASE_TYPE=postgresql
POSTGRES_USER=spectrum_user
POSTGRES_PASSWORD=secure_password_123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=spectrum_db

# Application Settings
APP_NAME="Spectrum Patient Management System"
DEBUG=True
ENVIRONMENT=development

# Security Settings (Development)
SECRET_KEY=dev_secret_key_change_in_production
JWT_SECRET_KEY=dev_jwt_secret_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# HIPAA Compliance Settings
ENABLE_AUDIT_LOGGING=True
ENABLE_ENCRYPTION=False
LOG_LEVEL=INFO
"""
    
    with open('.env.development', 'w') as f:
        f.write(env_content)
    
    logger.info("Created .env.development file")

def install_dependencies():
    """Install PostgreSQL dependencies"""
    logger.info("Installing PostgreSQL dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary", "alembic"], check=True)
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up PostgreSQL for Spectrum application")
    parser.add_argument("--docker", action="store_true", help="Set up using Docker")
    parser.add_argument("--local", action="store_true", help="Set up local PostgreSQL")
    parser.add_argument("--test", action="store_true", help="Test existing connection")
    
    args = parser.parse_args()
    
    if not any([args.docker, args.local, args.test]):
        print("Choose setup method:")
        print("1. Docker (recommended for development)")
        print("2. Local PostgreSQL installation")
        print("3. Test existing connection")
        
        choice = input("Enter choice (1/2/3): ").strip()
        
        if choice == "1":
            args.docker = True
        elif choice == "2":
            args.local = True
        elif choice == "3":
            args.test = True
        else:
            logger.error("Invalid choice")
            return False
    
    # Install dependencies first
    if not install_dependencies():
        return False
    
    # Create environment file
    create_env_file()
    
    # Load environment variables
    load_dotenv('.env.development')
    
    if args.docker:
        success = setup_docker_postgresql()
    elif args.local:
        success = setup_local_postgresql()
    elif args.test:
        success = test_postgresql_connection()
    
    if success:
        logger.info("\n✓ PostgreSQL setup completed successfully!")
        logger.info("You can now run the migration script: python migrate_sqlite_to_postgres.py")
    else:
        logger.error("\n✗ PostgreSQL setup failed")
        logger.error("Please check the error messages above and try again")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
