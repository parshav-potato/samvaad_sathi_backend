"""Database model for structure practice sessions."""

import datetime
import sqlalchemy
from sqlalchemy.orm import Mapped as SQLAlchemyMapped, mapped_column as sqlalchemy_mapped_column
from sqlalchemy.sql import functions as sqlalchemy_functions
from sqlalchemy.dialects.postgresql import JSONB

from src.repository.table import Base


class StructurePractice(Base):  # type: ignore
    """Model for structure practice sessions."""
    __tablename__ = "structure_practice"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    user_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interview_id: SQLAlchemyMapped[int | None] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("interview.id", ondelete="CASCADE"), nullable=True, index=True
    )
    track: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=64), nullable=False, index=True
    )
    questions: SQLAlchemyMapped[dict] = sqlalchemy_mapped_column(JSONB, nullable=False)
    # questions format: [{"question_id": 123, "text": "...", "structure_hint": "...", "index": 0}, ...]
    status: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=32), nullable=False, index=True, server_default=sqlalchemy.text("'active'")
    )
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    updated_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now(), onupdate=sqlalchemy_functions.now()
    )

    __mapper_args__ = {"eager_defaults": True}


class StructurePracticeAnswer(Base):  # type: ignore
    """Model for structure practice answers submitted by users."""
    __tablename__ = "structure_practice_answer"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    practice_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("structure_practice.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_index: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.Integer, nullable=False, index=True
    )
    answer_text: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.Text, nullable=False
    )
    time_spent_seconds: SQLAlchemyMapped[int | None] = sqlalchemy_mapped_column(
        sqlalchemy.Integer, nullable=True
    )
    analysis_result: SQLAlchemyMapped[dict | None] = sqlalchemy_mapped_column(JSONB, nullable=True)
    # analysis_result format: {"framework_progress": {...}, "time_per_section": {...}, "key_insight": "..."}
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )
    analyzed_at: SQLAlchemyMapped[datetime.datetime | None] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=True
    )

    __mapper_args__ = {"eager_defaults": True}
