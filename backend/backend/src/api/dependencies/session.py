import contextlib
import typing

import fastapi
from sqlalchemy.ext.asyncio import (
    async_sessionmaker as sqlalchemy_async_sessionmaker,
    AsyncSession as SQLAlchemyAsyncSession,
    AsyncSessionTransaction as SQLAlchemyAsyncSessionTransaction,
)

from src.repository.database import async_db


async def get_async_session() -> typing.AsyncGenerator[SQLAlchemyAsyncSession, None]:
    """
    Dependency that provides a database session for each request.
    Each request gets its own session instance for better concurrency.
    """
    # Get a new session instance for this request
    session = async_db.get_session()
    try:
        yield session
    except Exception as e:
        print(f"Database session error: {e}")
        await session.rollback()
        raise  # Re-raise the exception so FastAPI can handle it properly
    finally:
        await session.close()
