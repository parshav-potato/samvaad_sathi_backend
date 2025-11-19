import asyncio
from sqlalchemy import text
from src.repository.database import async_db

async def revert_migration():
    async with async_db.get_session() as session:
        try:
            # Get current version
            result = await session.execute(text('SELECT version_num FROM alembic_version'))
            current = result.scalar()
            print(f'Current version: {current}')
            
            # Drop the supplement column if it exists
            await session.execute(text('ALTER TABLE interview_question DROP COLUMN IF EXISTS supplement'))
            print('Dropped supplement column')
            
            # Update alembic version to previous (8f5f6d27c6e0)
            await session.execute(text("UPDATE alembic_version SET version_num = '8f5f6d27c6e0'"))
            
            await session.commit()
            print('Reverted alembic version to: 8f5f6d27c6e0')
            
        except Exception as e:
            print(f'Error: {e}')
            await session.rollback()

if __name__ == '__main__':
    asyncio.run(revert_migration())
