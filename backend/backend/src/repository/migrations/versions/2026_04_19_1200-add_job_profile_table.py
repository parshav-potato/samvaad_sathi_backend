"""add job profile table

Revision ID: job_profile_001
Revises: analytics_event_001
Create Date: 2026-04-19 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "job_profile_001"
down_revision = "analytics_event_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "job_profile" not in table_names:
        op.create_table(
            "job_profile",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_name", sa.String(length=160), nullable=False),
            sa.Column("job_description", sa.Text(), nullable=False),
            sa.Column("company_name", sa.String(length=256), nullable=True),
            sa.Column("experience_level", sa.String(length=64), nullable=True),
            sa.Column("skills", JSONB, nullable=True),
            sa.Column("additional_context", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    # Refresh inspector for idempotent/index-safe execution
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "job_profile" in table_names:
        existing_cols = {col["name"] for col in inspector.get_columns("job_profile")}

        # Backward-compatible additive guards for environments with partially applied schema
        if "job_name" not in existing_cols:
            op.add_column("job_profile", sa.Column("job_name", sa.String(length=160), nullable=True))
        if "job_description" not in existing_cols:
            op.add_column("job_profile", sa.Column("job_description", sa.Text(), nullable=True))
        if "company_name" not in existing_cols:
            op.add_column("job_profile", sa.Column("company_name", sa.String(length=256), nullable=True))
        if "experience_level" not in existing_cols:
            op.add_column("job_profile", sa.Column("experience_level", sa.String(length=64), nullable=True))
        if "skills" not in existing_cols:
            op.add_column("job_profile", sa.Column("skills", JSONB, nullable=True))
        if "additional_context" not in existing_cols:
            op.add_column("job_profile", sa.Column("additional_context", sa.Text(), nullable=True))
        if "created_by" not in existing_cols:
            op.add_column("job_profile", sa.Column("created_by", sa.Integer(), nullable=True))
        if "created_at" not in existing_cols:
            op.add_column(
                "job_profile",
                sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            )
        if "updated_at" not in existing_cols:
            op.add_column(
                "job_profile",
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            )

        existing_fk_specs = inspector.get_foreign_keys("job_profile")
        has_created_by_fk = any(
            fk.get("constrained_columns") == ["created_by"] and fk.get("referred_table") == "user"
            for fk in existing_fk_specs
        )
        fk_name = "fk_job_profile_created_by_user"
        if not has_created_by_fk and "created_by" in {col["name"] for col in inspector.get_columns("job_profile")}:
            op.create_foreign_key(
                fk_name,
                "job_profile",
                "user",
                ["created_by"],
                ["id"],
                ondelete="SET NULL",
            )

        existing_indexes = {idx["name"] for idx in inspector.get_indexes("job_profile")}
        idx_job_name = op.f("ix_job_profile_job_name")
        idx_created_by = op.f("ix_job_profile_created_by")
        idx_created_at = op.f("ix_job_profile_created_at")

        if idx_job_name not in existing_indexes:
            op.create_index(idx_job_name, "job_profile", ["job_name"], unique=False)
        if idx_created_by not in existing_indexes:
            op.create_index(idx_created_by, "job_profile", ["created_by"], unique=False)
        if idx_created_at not in existing_indexes:
            op.create_index(idx_created_at, "job_profile", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "job_profile" not in table_names:
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("job_profile")}
    for idx_name in (op.f("ix_job_profile_created_at"), op.f("ix_job_profile_created_by"), op.f("ix_job_profile_job_name")):
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name="job_profile")

    existing_fk_specs = inspector.get_foreign_keys("job_profile")
    fk_name = "fk_job_profile_created_by_user"
    if any(fk.get("name") == fk_name for fk in existing_fk_specs):
        op.drop_constraint(fk_name, "job_profile", type_="foreignkey")

    op.drop_table("job_profile")
