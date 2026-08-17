"""add student_id to user

Revision ID: 9889ca43eed1
Revises: dab6da149e6b
Create Date: 2026-08-16 23:23:12.587518

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9889ca43eed1'
down_revision = 'dab6da149e6b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("student_id", sa.String(length=128), nullable=True)
    )

    op.create_unique_constraint(
        "uq_user_student_id",
        "user",
        ["student_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_student_id",
        "user",
        type_="unique"
    )

    op.drop_column("user", "student_id")
