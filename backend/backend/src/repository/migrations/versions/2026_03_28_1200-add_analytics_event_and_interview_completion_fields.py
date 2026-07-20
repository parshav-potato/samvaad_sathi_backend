"""add analytics event table and interview completion fields

Revision ID: analytics_event_001
Revises: pacing_practice_001
Create Date: 2026-03-28 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "analytics_event_001"
down_revision = "pacing_practice_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    table_names = set(inspector.get_table_names())
    interview_columns = set()
    if "interview" in table_names:
        interview_columns = {col["name"] for col in inspector.get_columns("interview")}

    if "interview" in table_names and "completed_at" not in interview_columns:
        op.add_column("interview", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    if "interview" in table_names and "duration_seconds" not in interview_columns:
        op.add_column("interview", sa.Column("duration_seconds", sa.Integer(), nullable=True))

    if "interview" in table_names:
        interview_indexes = {idx["name"] for idx in inspector.get_indexes("interview")}
        interview_completed_idx = op.f("ix_interview_completed_at")
        if interview_completed_idx not in interview_indexes:
            op.create_index(interview_completed_idx, "interview", ["completed_at"], unique=False)

    if "analytics_event" not in table_names:
        op.create_table(
            "analytics_event",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("interview_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("event_data", JSONB, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.ForeignKeyConstraint(["interview_id"], ["interview.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    # refresh inspector after potential table create
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "analytics_event" in table_names:
        event_indexes = {idx["name"] for idx in inspector.get_indexes("analytics_event")}
        idx_created = op.f("ix_analytics_event_created_at")
        idx_type = op.f("ix_analytics_event_event_type")
        idx_interview = op.f("ix_analytics_event_interview_id")
        idx_user = op.f("ix_analytics_event_user_id")

        if idx_created not in event_indexes:
            op.create_index(idx_created, "analytics_event", ["created_at"], unique=False)
        if idx_type not in event_indexes:
            op.create_index(idx_type, "analytics_event", ["event_type"], unique=False)
        if idx_interview not in event_indexes:
            op.create_index(idx_interview, "analytics_event", ["interview_id"], unique=False)
        if idx_user not in event_indexes:
            op.create_index(idx_user, "analytics_event", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "analytics_event" in table_names:
        event_indexes = {idx["name"] for idx in inspector.get_indexes("analytics_event")}
        idx_user = op.f("ix_analytics_event_user_id")
        idx_interview = op.f("ix_analytics_event_interview_id")
        idx_type = op.f("ix_analytics_event_event_type")
        idx_created = op.f("ix_analytics_event_created_at")

        if idx_user in event_indexes:
            op.drop_index(idx_user, table_name="analytics_event")
        if idx_interview in event_indexes:
            op.drop_index(idx_interview, table_name="analytics_event")
        if idx_type in event_indexes:
            op.drop_index(idx_type, table_name="analytics_event")
        if idx_created in event_indexes:
            op.drop_index(idx_created, table_name="analytics_event")
        op.drop_table("analytics_event")

    if "interview" in table_names:
        interview_indexes = {idx["name"] for idx in inspector.get_indexes("interview")}
        interview_cols = {col["name"] for col in inspector.get_columns("interview")}
        interview_completed_idx = op.f("ix_interview_completed_at")

        if interview_completed_idx in interview_indexes:
            op.drop_index(interview_completed_idx, table_name="interview")
        if "duration_seconds" in interview_cols:
            op.drop_column("interview", "duration_seconds")
        if "completed_at" in interview_cols:
            op.drop_column("interview", "completed_at")
