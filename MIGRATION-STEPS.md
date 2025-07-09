# Step-by-Step PostgreSQL Migration Instructions

## Tomorrow's Migration Process

Follow these steps **exactly** in order to migrate from SQLite to PostgreSQL safely:

### 📋 Pre-Migration Checklist

✅ **Before you start:**
1. Ensure your current SQLite application is working
2. Create a backup of your current `people.db`
3. Have about 30-60 minutes available
4. Ensure stable internet connection (if using Docker)

### 🔧 Step 1: Set Up PostgreSQL (Choose ONE option)

#### Option A: Docker Setup (Recommended)
```powershell
# Run this in PowerShell as Administrator
python setup_postgresql.py --docker
```

This will:
- Install required dependencies
- Set up PostgreSQL in Docker
- Create the database and user
- Test the connection
- Create the `.env.development` file

#### Option B: Local PostgreSQL Installation
```powershell
python setup_postgresql.py --local
```

Follow the prompts to install PostgreSQL locally.

### 🗄️ Step 2: Verify PostgreSQL Setup

```powershell
python db_manager.py status
```

You should see:
- Database Type: postgresql
- Connection: ✓ Healthy
- Tables count and database size

### 🔄 Step 3: Run the Migration

```powershell
python migrate_sqlite_to_postgres.py
```

**What this script does:**
1. Creates an automatic backup of your SQLite database
2. Connects to PostgreSQL
3. Creates all tables using your existing models
4. Transfers all data preserving relationships
5. Verifies the migration was successful

**Expected output:**
```
Starting SQLite to PostgreSQL migration...
SQLite database backed up to people_backup_migration_YYYYMMDD_HHMMSS.db
PostgreSQL connection successful
PostgreSQL tables created successfully
Migrating table: patients
Migrated batch 1 for table patients
Migrating table: services
...
✓ Table patients: X rows migrated successfully
✓ Table services: Y rows migrated successfully
Migration verification completed successfully!
Migration completed successfully!
```

### 🔧 Step 4: Update Your Application

Replace your current `database.py` with the PostgreSQL version:

```powershell
# Backup your current database.py
copy database.py database_sqlite_backup.py

# Replace with PostgreSQL version
copy database_postgres.py database.py
```

### ✅ Step 5: Test Your Application

```powershell
# Start your application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Test these key functions:**
1. Open http://localhost:8000
2. Login with your credentials
3. View patient list
4. Add a new patient
5. Edit an existing patient
6. Check that all data is present

### 🗄️ Step 6: Verify Data Integrity

```powershell
python db_manager.py status
```

Compare the row counts with your original SQLite database to ensure all data was migrated.

### 🎯 Step 7: Update Environment Configuration

1. **Development**: Your `.env.development` is already configured
2. **Production**: Update your `.env.production` file:

```env
DATABASE_TYPE=postgresql
POSTGRES_USER=your_production_user
POSTGRES_PASSWORD=your_production_password
POSTGRES_HOST=your_production_host
POSTGRES_PORT=5432
POSTGRES_DB=your_production_db
```

### 🔄 Step 8: Set Up Future Migrations (Optional)

For future database changes, use Alembic:

```powershell
# Initialize Alembic (already done for you)
# alembic init alembic

# Create a new migration when you change models
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

## 🆘 Troubleshooting

### Common Issues and Solutions

#### 1. "Connection refused" error
```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

**Solutions:**
- If using Docker: `docker start spectrum-postgres`
- Check if PostgreSQL is running: `docker ps` or check Windows Services
- Verify port 5432 is not blocked by firewall

#### 2. "Authentication failed" error
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**Solutions:**
- Check your `.env.development` file has correct credentials
- If using Docker, use: `spectrum_user` / `secure_password_123`
- Reset Docker container: `python setup_postgresql.py --docker`

#### 3. "Database does not exist" error
```
psycopg2.OperationalError: FATAL: database "spectrum_db" does not exist
```

**Solutions:**
- Re-run the setup script: `python setup_postgresql.py --docker`
- Manually create database in PostgreSQL

#### 4. "ImportError: No module named 'psycopg2'"
```powershell
pip install psycopg2-binary
```

#### 5. Migration script fails midway
**Don't panic!** Your original SQLite database is safe.

1. Check the backup was created: `people_backup_migration_*.db`
2. Check PostgreSQL connection: `python db_manager.py status`
3. Re-run migration: `python migrate_sqlite_to_postgres.py`
4. If still failing, revert to SQLite and contact support

### 🔙 Rollback Procedure (if needed)

If something goes wrong, you can always rollback:

```powershell
# Restore your original database configuration
copy database_sqlite_backup.py database.py

# Your original people.db file is untouched
# Start your application normally
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📈 Post-Migration Benefits

After successful migration, you'll have:

1. **Better Performance**: PostgreSQL handles concurrent users much better
2. **Data Integrity**: ACID compliance and better constraint enforcement
3. **Scalability**: Ready for production deployment on AWS
4. **Advanced Features**: JSON columns, full-text search, better indexing
5. **Production Ready**: Proper connection pooling and optimization

## 🚀 Next Steps After Migration

1. **Test thoroughly**: Ensure all functionality works
2. **Update documentation**: Note the new database requirements
3. **Configure monitoring**: Set up database monitoring
4. **Plan backups**: Set up automated PostgreSQL backups
5. **Optimize performance**: Add indexes for frequently queried columns

## 📞 Support

If you encounter any issues during migration:

1. **Check the logs**: Migration script provides detailed logging
2. **Database status**: Run `python db_manager.py status`
3. **Backup is safe**: Your original SQLite database is preserved
4. **Easy rollback**: You can always revert to SQLite if needed

Remember: This migration is reversible, and your data is always safe! 

The migration typically takes 5-15 minutes depending on your data size.
