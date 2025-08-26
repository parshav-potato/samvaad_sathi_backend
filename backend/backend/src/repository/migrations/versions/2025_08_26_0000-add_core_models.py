"""add core models for user, session, interview, question_attempt, report

Revision ID: add_core_models_20250826
Revises: 60d1844cb5d3
Create Date: 2025-08-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_core_models_20250826"
down_revision = "60d1844cb5d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=1024), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("years_experience", sa.Float(), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.create_table(
        "session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_session_user_id"), "session", ["user_id"], unique=False)
    op.create_index(op.f("ix_session_token"), "session", ["token"], unique=True)

    op.create_table(
        "interview",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("track", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_user_id"), "interview", ["user_id"], unique=False)
    op.create_index(op.f("ix_interview_track"), "interview", ["track"], unique=False)
    op.create_index(op.f("ix_interview_status"), "interview", ["status"], unique=False)

    op.create_table(
        "question_attempt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.String(length=512), nullable=True),
        sa.Column("transcription", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interview.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_attempt_interview_id"), "question_attempt", ["interview_id"], unique=False)

    op.create_table(
        "report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("knowledge_competence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("speech_structure_fluency", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["interview_id"], ["interview.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_interview_id"), "report", ["interview_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_interview_id"), table_name="report")
    op.drop_table("report")
    op.drop_index(op.f("ix_question_attempt_interview_id"), table_name="question_attempt")
    op.drop_table("question_attempt")
    op.drop_index(op.f("ix_interview_status"), table_name="interview")
    op.drop_index(op.f("ix_interview_track"), table_name="interview")
    op.drop_index(op.f("ix_interview_user_id"), table_name="interview")
    op.drop_table("interview")
    op.drop_index(op.f("ix_session_token"), table_name="session")
    op.drop_index(op.f("ix_session_user_id"), table_name="session")
    op.drop_table("session")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")


