# --- PostgreSQL-Only Database Configuration ---
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

# Load environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dannynico011")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "spectrum_db")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("POSTGRES_POOL_SIZE", 20)),
    max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", 30)),
    pool_pre_ping=True,
    pool_recycle=int(os.getenv("POSTGRES_POOL_RECYCLE", 1800)),
    echo=os.getenv("POSTGRES_ECHO_SQL", "False").lower() == "true",
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# PostgreSQL-specific settings
@event.listens_for(Engine, "connect")
def set_postgresql_search_path(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, 'cursor'):
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
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Get database info
def get_database_info():
    return {
        "database_type": "postgresql",
        "database_url": SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL,
        "engine_pool_size": getattr(engine.pool, 'size', None),
        "engine_pool_checked_out": getattr(engine.pool, 'checkedout', None),
        "connection_healthy": check_database_connection()
    }