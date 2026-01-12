"""Database model for pronunciation practice sessions."""

import datetime
import sqlalchemy
from sqlalchemy.orm import Mapped as SQLAlchemyMapped, mapped_column as sqlalchemy_mapped_column, relationship
from sqlalchemy.sql import functions as sqlalchemy_functions
from sqlalchemy.dialects.postgresql import JSONB

from src.repository.table import Base


class PronunciationPractice(Base):  # type: ignore
    """Model for pronunciation practice sessions."""
    __tablename__ = "pronunciation_practice"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    user_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    difficulty: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=16), nullable=False, index=True
    )
    words: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False)
    # words format: [{"word": "communication", "phonetic": "kə·myü·nə·kā·shən", "index": 0}, ...]
    status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=32), nullable=False, index=True, default="active"
    )
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    user = relationship("User", back_populates="pronunciation_practices")

    __mapper_args__ = {"eager_defaults": True}
