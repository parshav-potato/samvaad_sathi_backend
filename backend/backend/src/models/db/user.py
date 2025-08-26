import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped, mapped_column as sqlalchemy_mapped_column, relationship
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class User(Base):  # type: ignore
    __tablename__ = "user"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    email: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(
        sqlalchemy.String(length=254), nullable=False, unique=True, index=True
    )
    password_hash: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=1024), nullable=False)
    name: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=128), nullable=False)
    resume_text: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(sqlalchemy.Text, nullable=True)
    years_experience: SQLAlchemyMapped[float | None] = sqlalchemy_mapped_column(sqlalchemy.Float, nullable=True)
    skills: SQLAlchemyMapped[dict | None] = sqlalchemy_mapped_column(JSONB, nullable=True)
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    interviews = relationship(
        "Interview", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    __mapper_args__ = {"eager_defaults": True}


