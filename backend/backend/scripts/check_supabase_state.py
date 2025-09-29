import asyncio
import asyncpg

async def check_supabase_tables():
    """Check what tables exist in Supabase"""
    try:
        conn = await asyncpg.connect(
            host='your-supabase-host.supabase.co',
            port=5432,
            user='postgres',
            password='your-supabase-password',
            database='postgres',
            ssl='require'
        )
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print("Existing tables in Supabase:")
        for table in tables:
            print(f"  - {table['tablename']}")
        
        # Check alembic version table
        try:
            version = await conn.fetchval("SELECT version_num FROM alembic_version")
            print(f"\nCurrent Alembic version: {version}")
        except:
            print("\nNo alembic_version table found")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error checking Supabase: {e}")

if __name__ == "__main__":
    asyncio.run(check_supabase_tables())
