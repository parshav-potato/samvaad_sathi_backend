import datetime

import sqlalchemy
from sqlalchemy.orm import Mapped as SQLAlchemyMapped, mapped_column as sqlalchemy_mapped_column, relationship
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class UserResume(Base):  # type: ignore
    __tablename__ = "user_resume"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    user_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    s3_key: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=512), nullable=False)
    filename: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=256), nullable=False)
    resume_text: SQLAlchemyMapped[str | None] = sqlalchemy_mapped_column(sqlalchemy.Text, nullable=True)
    source: SQLAlchemyMapped[str] = sqlalchemy_mapped_column(sqlalchemy.String(length=32), nullable=False)
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    user = relationship("User", back_populates="resumes")

    __mapper_args__ = {"eager_defaults": True}
