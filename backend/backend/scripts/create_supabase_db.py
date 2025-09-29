import asyncio
import asyncpg

async def create_app_database():
    """Create the app database on Supabase"""
    try:
        # Connect to postgres database first with SSL context
        # Note: Supabase databases are typically pre-created, this script is for reference
        conn = await asyncpg.connect(
            host='your-supabase-host.supabase.co',
            port=5432,
            user='postgres',
            password='your-supabase-password',
            database='postgres',
            ssl='require'
        )
        
        # Check if database exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'app'")
        
        if exists:
            print("Database 'app' already exists")
        else:
            # Create the database
            await conn.execute('CREATE DATABASE app;')
            print("Database 'app' created successfully")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    asyncio.run(create_app_database())
