import asyncio
import asyncpg

async def create_app_database():
    """Create the app database on Aurora"""
    try:
        # Connect to postgres database first with SSL context
        conn = await asyncpg.connect(
            host='samvaad-sathi-instance-1.cjicoyuguai3.ap-south-1.rds.amazonaws.com',
            port=5432,
            user='postgres',
            password='postgres',
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
