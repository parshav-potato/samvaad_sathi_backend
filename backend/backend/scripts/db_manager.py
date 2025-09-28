#!/usr/bin/env python3
"""
Database Management Script for Samvaad Sathi Backend

This script provides utilities to manage the database without the destructive
table recreation that happens on each application startup.

Usage:
    python scripts/db_manager.py init      # Initialize database with current schema
    python scripts/db_manager.py migrate   # Run pending migrations
    python scripts/db_manager.py reset     # Reset database (DESTRUCTIVE - dev only)
    python scripts/db_manager.py status    # Show migration status
"""

import asyncio
import sys
from pathlib import Path
import subprocess
import os
from typing import Optional

# Add the parent directory to Python path to import src modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.repository.database import async_db
from src.repository.table import Base
from src.config.manager import settings
import src.models.db  # Import all models


class DatabaseManager:
    """Manages database operations safely"""
    
    def __init__(self):
        self.engine = async_db.async_engine
        
    async def check_connection(self) -> bool:
        """Test database connection"""
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    async def check_alembic_setup(self) -> bool:
        """Check if Alembic is properly set up"""
        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')")
                )
                return result.scalar()
        except Exception:
            return False
    
    async def get_migration_status(self) -> dict:
        """Get current migration status"""
        try:
            # Run alembic current command
            result = subprocess.run(
                ["python", "-m", "alembic", "current"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            current = result.stdout.strip() if result.returncode == 0 else "No migrations"
            
            # Run alembic heads command  
            result = subprocess.run(
                ["python", "-m", "alembic", "heads"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            heads = result.stdout.strip() if result.returncode == 0 else "No heads"
            
            return {
                "current": current,
                "heads": heads,
                "up_to_date": current in heads if current != "No migrations" else False
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def initialize_database(self) -> bool:
        """Initialize database with proper migration setup"""
        print("Initializing database...")
        
        if not await self.check_connection():
            return False
            
        # Check if alembic is set up
        if not await self.check_alembic_setup():
            print("Setting up Alembic migration tracking...")
            
            # Run alembic stamp head to mark current schema as up-to-date
            result = subprocess.run(
                ["python", "-m", "alembic", "stamp", "head"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Failed to initialize Alembic: {result.stderr}")
                return False
                
            print("Alembic migration tracking initialized")
        else:
            print("Alembic already set up, running pending migrations...")
            await self.run_migrations()
            
        return True
    
    async def run_migrations(self) -> bool:
        """Run pending migrations"""
        print("Running database migrations...")
        
        try:
            result = subprocess.run(
                ["python", "-m", "alembic", "upgrade", "head"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Migrations completed successfully")
                if result.stdout.strip():
                    print(f"Output: {result.stdout}")
                return True
            else:
                print(f"Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error running migrations: {e}")
            return False
    
    async def reset_database(self, confirm: bool = False) -> bool:
        """Reset database (DESTRUCTIVE - development only)"""
        if not confirm:
            print("WARNING: This will DELETE ALL DATA in the database!")
            response = input("Are you sure you want to continue? Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("Operation cancelled")
                return False
        
        if settings.ENVIRONMENT == "PROD":
            print("Database reset is not allowed in production environment")
            return False
            
        print("Resetting database...")
        
        try:
            async with self.engine.begin() as connection:
                print("Using schema drop and recreate approach...")
                
                # First, terminate all other connections to the database
                print("Terminating active database connections...")
                await connection.execute(text("""
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database() 
                    AND pid <> pg_backend_pid()
                """))
                print("Terminated active connections")
                
                # Drop the entire public schema and recreate it
                # This is more reliable than dropping individual tables
                await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                print("Dropped public schema")
                
                await connection.execute(text("CREATE SCHEMA public"))
                print("Created public schema")
                
                await connection.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
                await connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
                print("Granted permissions on public schema")
                
                # Create all tables
                print("Creating all tables from current schema...")
                await connection.run_sync(Base.metadata.create_all)
                print("Created all tables from current schema")
                
                # Mark as up-to-date with migrations
                print("Updating Alembic version...")
                try:
                    result = subprocess.run(
                        ["python", "-m", "alembic", "stamp", "head"],
                        cwd=Path(__file__).parent.parent,
                        capture_output=True,
                        text=True,
                        timeout=30  # 30 second timeout
                    )
                    
                    if result.returncode == 0:
                        print("Database reset complete and marked as up-to-date")
                        return True
                    else:
                        print(f"Database reset complete but failed to update Alembic: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    print("Alembic stamp timed out - database reset complete but Alembic version not updated")
                    print("You can manually run: python -m alembic stamp head")
                    return True
                    
        except Exception as e:
            print(f"Error resetting database: {e}")
            return False
    
    async def show_status(self) -> None:
        """Show current database and migration status"""
        print("Database Status")
        print("=" * 50)
        
        # Connection test
        if await self.check_connection():
            print("Database connection: OK")
        else:
            print("Database connection: FAILED")
            return
        
        # Environment info
        print(f"Environment: {settings.ENVIRONMENT}")
        print(f"Database: {settings.DB_POSTGRES_NAME} @ {settings.DB_POSTGRES_HOST}:{settings.DB_POSTGRES_PORT}")
        
        # Alembic status
        if await self.check_alembic_setup():
            print("Alembic migrations: ENABLED")
            status = await self.get_migration_status()
            if "error" in status:
                print(f"Migration status error: {status['error']}")
            else:
                print(f"Current revision: {status.get('current', 'Unknown')}")
                print(f"Latest revision: {status.get('heads', 'Unknown')}")
                if status.get('up_to_date'):
                    print("Migrations: UP TO DATE")
                else:
                    print("Migrations: PENDING UPDATES AVAILABLE")
        else:
            print("Alembic migrations: NOT INITIALIZED")
            print("   Run 'python scripts/db_manager.py init' to set up migrations")


async def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    manager = DatabaseManager()
    
    try:
        if command == "init":
            success = await manager.initialize_database()
            sys.exit(0 if success else 1)
            
        elif command == "migrate":
            success = await manager.run_migrations()
            sys.exit(0 if success else 1)
            
        elif command == "reset":
            success = await manager.reset_database()
            sys.exit(0 if success else 1)
            
        elif command == "status":
            await manager.show_status()
            
        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
