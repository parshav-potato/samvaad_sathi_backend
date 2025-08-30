import boto3
import pydantic
from sqlalchemy.ext.asyncio import (
    AsyncEngine as SQLAlchemyAsyncEngine,
    AsyncSession as SQLAlchemyAsyncSession,
    create_async_engine as create_sqlalchemy_async_engine,
)
from sqlalchemy.pool import Pool as SQLAlchemyPool

from src.config.manager import settings


class AuroraDatabase:
    def __init__(self):
        self.postgres_uri = self._build_connection_uri()
        self.async_engine: SQLAlchemyAsyncEngine = create_sqlalchemy_async_engine(
            url=self.set_async_db_uri,
            echo=settings.IS_DB_ECHO_LOG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_POOL_OVERFLOW,
            pool_timeout=settings.DB_TIMEOUT,
            # Aurora-specific optimizations
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        self.async_session: SQLAlchemyAsyncSession = SQLAlchemyAsyncSession(
            bind=self.async_engine,
            expire_on_commit=settings.IS_DB_EXPIRE_ON_COMMIT,
        )
        self.pool: SQLAlchemyPool = self.async_engine.pool

    def _build_connection_uri(self) -> str:
        """Build Aurora connection URI with optional IAM authentication"""
        if settings.USE_IAM_AUTH:
            # Use IAM authentication for Aurora
            return self._get_iam_auth_uri()
        else:
            # Standard password authentication
            return f"{settings.DB_POSTGRES_SCHEMA}://{settings.DB_POSTGRES_USERNAME}:{settings.DB_POSTGRES_PASSWORD}@{settings.DB_POSTGRES_HOST}:{settings.DB_POSTGRES_PORT}/{settings.DB_POSTGRES_NAME}"

    def _get_iam_auth_uri(self) -> str:
        """Generate Aurora connection URI with IAM authentication token"""
        client = boto3.client(
            'rds',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        # Generate IAM auth token (valid for 15 minutes)
        token = client.generate_db_auth_token(
            DBHostname=settings.DB_POSTGRES_HOST,
            Port=settings.DB_POSTGRES_PORT,
            DBUsername=settings.DB_POSTGRES_USERNAME,
            Region=settings.AWS_REGION
        )
        
        return f"{settings.DB_POSTGRES_SCHEMA}://{settings.DB_POSTGRES_USERNAME}:{token}@{settings.DB_POSTGRES_HOST}:{settings.DB_POSTGRES_PORT}/{settings.DB_POSTGRES_NAME}?sslmode=require"

    @property
    def set_async_db_uri(self) -> str:
        """
        Set the synchronous database driver into asynchronous version by utilizing AsyncPG:
        postgresql:// => postgresql+asyncpg://
        """
        return self.postgres_uri.replace("postgresql://", "postgresql+asyncpg://")


# Global instance
async_aurora_db: AuroraDatabase = AuroraDatabase()
