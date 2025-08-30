import asyncio
import asyncpg

async def check_aurora_tables():
    """Check what tables exist in Aurora"""
    try:
        conn = await asyncpg.connect(
            host='samvaad-sathi-instance-1.cjicoyuguai3.ap-south-1.rds.amazonaws.com',
            port=5432,
            user='postgres',
            password='postgres',
            database='app',
            ssl='require'
        )
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print("Existing tables in Aurora:")
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
        print(f"Error checking Aurora: {e}")

if __name__ == "__main__":
    asyncio.run(check_aurora_tables())
