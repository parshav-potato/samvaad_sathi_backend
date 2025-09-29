import pydantic
from sqlalchemy.ext.asyncio import (
    AsyncEngine as SQLAlchemyAsyncEngine,
    AsyncSession as SQLAlchemyAsyncSession,
    create_async_engine as create_sqlalchemy_async_engine,
)
from sqlalchemy.pool import Pool as SQLAlchemyPool

from src.config.manager import settings


class SupabaseDatabase:
    def __init__(self):
        self.postgres_uri = self._build_connection_uri()
        self.async_engine: SQLAlchemyAsyncEngine = create_sqlalchemy_async_engine(
            url=self.set_async_db_uri,
            echo=settings.IS_DB_ECHO_LOG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_POOL_OVERFLOW,
            pool_timeout=settings.DB_TIMEOUT,
            # Supabase optimizations
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        self.async_session: SQLAlchemyAsyncSession = SQLAlchemyAsyncSession(
            bind=self.async_engine,
            expire_on_commit=settings.IS_DB_EXPIRE_ON_COMMIT,
        )
        self.pool: SQLAlchemyPool = self.async_engine.pool

    def _build_connection_uri(self) -> str:
        """Build Supabase connection URI"""
        # Standard password authentication for Supabase
        return f"{settings.DB_POSTGRES_SCHEMA}://{settings.DB_POSTGRES_USERNAME}:{settings.DB_POSTGRES_PASSWORD}@{settings.DB_POSTGRES_HOST}:{settings.DB_POSTGRES_PORT}/{settings.DB_POSTGRES_NAME}?sslmode=require"

    @property
    def set_async_db_uri(self) -> str:
        """
        Set the synchronous database driver into asynchronous version by utilizing AsyncPG:
        postgresql:// => postgresql+asyncpg://
        """
        return self.postgres_uri.replace("postgresql://", "postgresql+asyncpg://")


# Global instance
async_supabase_db: SupabaseDatabase = SupabaseDatabase()
