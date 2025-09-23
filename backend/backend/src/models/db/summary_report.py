import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped as SQLAlchemyMapped, mapped_column as sqlalchemy_mapped_column, relationship
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.repository.table import Base


class SummaryReport(Base):  # type: ignore
    __tablename__ = "summary_report"

    id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(primary_key=True, autoincrement="auto")
    interview_id: SQLAlchemyMapped[int] = sqlalchemy_mapped_column(
        sqlalchemy.ForeignKey("interview.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    report_json: SQLAlchemyMapped[dict | None] = sqlalchemy_mapped_column(JSONB, nullable=True)
    created_at: SQLAlchemyMapped[datetime.datetime] = sqlalchemy_mapped_column(
        sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy_functions.now()
    )

    interview = relationship("Interview")

    __mapper_args__ = {"eager_defaults": True}
