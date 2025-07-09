# PostgreSQL Migration Guide

## Overview
This guide will help you migrate your FastAPI patient management system from SQLite to PostgreSQL. This migration is essential for production deployment and provides better performance, concurrency, and features.

## Prerequisites
- PostgreSQL 14+ installed locally or Docker
- Python 3.8+
- Your current SQLite database (`people.db`)

## Step-by-Step Migration Process

### 1. Install PostgreSQL Dependencies
```bash
pip install psycopg2-binary alembic
```

### 2. PostgreSQL Setup Options

#### Option A: Local PostgreSQL Installation
1. Download and install PostgreSQL from https://www.postgresql.org/download/
2. Create a database and user for your application
3. Update your `.env` file with PostgreSQL credentials

#### Option B: Docker PostgreSQL (Recommended for Development)
```bash
docker run --name spectrum-postgres \
  -e POSTGRES_DB=spectrum_db \
  -e POSTGRES_USER=spectrum_user \
  -e POSTGRES_PASSWORD=your_secure_password \
  -p 5432:5432 \
  -d postgres:14
```

### 3. Environment Configuration
Create a `.env.development` file with PostgreSQL settings.

### 4. Database Configuration Update
Update `database.py` to support both SQLite (development) and PostgreSQL (production).

### 5. Data Migration
Use the provided migration script to transfer your existing SQLite data to PostgreSQL.

### 6. Testing
Verify all data has been migrated correctly and all API endpoints work.

## Benefits of PostgreSQL Migration

### Performance
- Better performance with large datasets
- Advanced indexing capabilities
- Optimized query execution plans

### Concurrency
- Multi-user support without database locking
- Better handling of concurrent requests
- ACID compliance for data integrity

### Features
- Advanced data types (JSON, arrays, etc.)
- Full-text search capabilities
- Spatial data support with PostGIS
- Better backup and recovery options

### Security
- Row-level security for HIPAA compliance
- Advanced user permissions
- Audit logging capabilities

### Scalability
- Horizontal scaling with read replicas
- Partitioning for large tables
- Connection pooling

## Migration Files Provided

1. `database_postgres.py` - Updated database configuration
2. `migrate_sqlite_to_postgres.py` - Data migration script
3. `alembic.ini` - Alembic configuration for future migrations
4. `alembic/` - Migration environment setup
5. `.env.development` - Development environment variables
6. `requirements_postgres.txt` - Updated dependencies

## Post-Migration Steps

1. Update your production configuration
2. Set up automated backups
3. Configure monitoring
4. Update your CI/CD pipeline
5. Test HIPAA compliance features

## Rollback Plan

If issues arise, you can always rollback to SQLite:
1. Rename `database.py.backup` back to `database.py`
2. Use your existing `people.db` file
3. Remove PostgreSQL dependencies

## Support

If you encounter any issues during migration:
1. Check the migration logs
2. Verify PostgreSQL connection settings
3. Ensure all dependencies are installed
4. Review the troubleshooting section below

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check PostgreSQL is running
   - Verify port 5432 is available
   - Check firewall settings

2. **Authentication Failed**
   - Verify username/password in `.env`
   - Check PostgreSQL user permissions
   - Ensure database exists

3. **Migration Errors**
   - Check SQLite database integrity
   - Verify PostgreSQL version compatibility
   - Review migration script logs

### Performance Optimization

After migration, consider these optimizations:
1. Create indexes on frequently queried columns
2. Analyze table statistics
3. Configure connection pooling
4. Set up query monitoring

This migration will significantly improve your application's performance and prepare it for production deployment on AWS!
