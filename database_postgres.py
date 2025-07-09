import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
import sqlite3

# Environment-based database configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite or postgresql
POSTGRES_USER = os.getenv("POSTGRES_USER", "spectrum_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "spectrum_db")

# Database URL configuration
if DATABASE_TYPE == "postgresql":
    SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # PostgreSQL engine with connection pooling
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,  # Validates connections before use
        pool_recycle=1800,   # Recycle connections every 30 minutes
        echo=False,          # Set to True for SQL debugging
        future=True          # Use SQLAlchemy 2.0 style
    )
else:
    # SQLite configuration (for development/testing)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./people.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLite-specific configuration (only for SQLite)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Better performance
        cursor.execute("PRAGMA cache_size=1000")  # Increase cache
        cursor.execute("PRAGMA temp_store=memory")  # Use memory for temp tables
        cursor.close()

# PostgreSQL-specific configuration
@event.listens_for(Engine, "connect")
def set_postgresql_search_path(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, 'cursor') and not isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check function
def check_database_connection():
    """Check if database connection is healthy"""
    try:
        db = SessionLocal()
        # Simple query to test connection
        if DATABASE_TYPE == "postgresql":
            db.execute("SELECT 1")
        else:
            db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Get database info
def get_database_info():
    """Return information about the current database configuration"""
    return {
        "database_type": DATABASE_TYPE,
        "database_url": SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL,
        "engine_pool_size": getattr(engine.pool, 'size', None),
        "engine_pool_checked_out": getattr(engine.pool, 'checkedout', None),
        "connection_healthy": check_database_connection()
    }
