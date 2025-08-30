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
    try:
        yield async_db.async_session
    except Exception as e:
        print(f"Database session error: {e}")
        await async_db.async_session.rollback()
        raise  # Re-raise the exception so FastAPI can handle it properly
    finally:
        await async_db.async_session.close()
