# Database Persistence and Multi-Instance Support

## Overview

The database configuration has been updated to ensure persistence across application restarts and support for multiple concurrent instances.

## Key Changes Made

### 1. Removed Destructive Table Recreation
**Before**: Every application startup would drop all tables and recreate them:
```python
await connection.run_sync(Base.metadata.drop_all)  # DESTRUCTIVE!
await connection.run_sync(Base.metadata.create_all)
```

**After**: Safe initialization that preserves existing data:
```python
# Check if Alembic migrations are set up
if has_alembic_version:
    # Use proper migrations for schema management
    logger.info("Database managed by Alembic migrations")
else:
    # Fallback: create tables only if they don't exist
    await connection.run_sync(Base.metadata.create_all, checkfirst=True)
```

### 2. Session Factory for Better Concurrency
**Before**: Single shared session instance:
```python
self.async_session: SQLAlchemyAsyncSession = SQLAlchemyAsyncSession(...)
```

**After**: Session factory that creates new sessions per request:
```python
self.async_session_factory = sqlalchemy_async_sessionmaker(...)

def get_session(self) -> SQLAlchemyAsyncSession:
    return self.async_session_factory()
```

### 3. Database Management Tools
- `scripts/db_manager.py`: CLI tool for database operations
- `scripts/test_db_persistence.py`: Test script for verification

## Database Management Commands

### Check Database Status
```powershell
python scripts/db_manager.py status
```

### Initialize Database (First Time Setup)
```powershell
python scripts/db_manager.py init
```

### Run Database Migrations
```powershell
python scripts/db_manager.py migrate
```

### Reset Database (Development Only)
```powershell
python scripts/db_manager.py reset
```

## Testing Persistence

### Test Database Persistence
```powershell
python scripts/test_db_persistence.py
```

### Test with Cleanup
```powershell
python scripts/test_db_persistence.py --cleanup
```

## Multi-Instance Support

The updated configuration supports multiple application instances:

1. **Connection Pooling**: Each instance maintains its own connection pool
2. **Session Isolation**: Each request gets its own database session
3. **Transaction Safety**: Proper rollback handling for failed operations
4. **Aurora Optimizations**: Connection recycling and SSL requirements

## Best Practices

### For Development
1. Use `python scripts/db_manager.py status` to check database state
2. Use Alembic migrations for schema changes: `alembic revision --autogenerate -m "description"`
3. Run migrations with: `python scripts/db_manager.py migrate`

### For Production
1. **Never** use `db_manager.py reset` in production
2. Always run migrations before deploying: `alembic upgrade head`
3. Monitor connection pool metrics
4. Set appropriate pool sizes in environment variables

### For Testing
1. Use separate test databases
2. Run `test_db_persistence.py` to verify setup
3. Test with multiple instances running simultaneously

## Environment Variables

Ensure these are properly configured in your `.env` file:

```env
# Database Connection
POSTGRES_HOST=your-aurora-cluster.cluster-xxx.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-secure-password

# Connection Pool Settings
DB_POOL_SIZE=5                    # Base pool size
DB_MAX_POOL_CON=5                # Maximum pool connections
DB_POOL_OVERFLOW=10              # Additional overflow connections
DB_TIMEOUT=30                    # Connection timeout

# Session Behavior
IS_DB_EXPIRE_ON_COMMIT=False     # Don't expire objects on commit
IS_DB_FORCE_ROLLBACK=False       # Don't force rollback
IS_DB_ECHO_LOG=False             # Set to True for SQL query logging
```

## Migration Workflow

### Creating New Migrations
```powershell
# 1. Make changes to your SQLAlchemy models
# 2. Generate migration
alembic revision --autogenerate -m "Add new feature"

# 3. Review generated migration in src/repository/migrations/versions/
# 4. Apply migration
alembic upgrade head
```

### Checking Migration Status
```powershell
alembic current              # Current revision
alembic heads               # Latest available revision
alembic history             # Full migration history
```

## Troubleshooting

### Database Connection Issues
1. Check Aurora cluster status in AWS console
2. Verify network connectivity and security groups
3. Confirm credentials and SSL configuration

### Migration Issues
1. Check `alembic current` vs `alembic heads`
2. Review migration files for conflicts
3. Use `python scripts/db_manager.py status` for overview

### Performance Issues
1. Monitor connection pool utilization
2. Adjust pool settings based on load
3. Use `IS_DB_ECHO_LOG=True` to debug slow queries

## Security Considerations

1. **SSL Required**: All connections use SSL for Aurora
2. **Connection Validation**: `pool_pre_ping=True` validates connections
3. **Session Isolation**: Each request gets isolated session
4. **Credential Management**: Use environment variables, not hardcoded values
