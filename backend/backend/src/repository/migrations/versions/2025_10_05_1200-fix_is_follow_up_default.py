"""ensure is_follow_up has default false and no nulls

Revision ID: 4c3d5c7aa1a0
Revises: 3a2c1f4b8b10
Create Date: 2025-10-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c3d5c7aa1a0'
down_revision = '3a2c1f4b8b10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill any existing NULLs to False, then enforce default False for future inserts
    op.execute("UPDATE interview_question SET is_follow_up = false WHERE is_follow_up IS NULL")
    op.alter_column(
        "interview_question",
        "is_follow_up",
        server_default=sa.text("false"),
        existing_type=sa.Boolean(),
        nullable=False,
    )


def downgrade() -> None:
    # Leave data intact but remove server default to revert prior state
    op.alter_column(
        "interview_question",
        "is_follow_up",
        server_default=None,
        existing_type=sa.Boolean(),
        nullable=False,
    )

