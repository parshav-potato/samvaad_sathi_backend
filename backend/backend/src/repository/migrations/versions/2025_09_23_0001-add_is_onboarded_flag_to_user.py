"""Add is_onboarded flag to user table

Revision ID: b1a2c3d4e5f6
Revises: 0ab50c01c7d7
Create Date: 2025-09-23 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1a2c3d4e5f6'
down_revision = 'e4792e2a1b7c'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('is_onboarded', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Optional: set existing users to false explicitly (server_default already handles this)


def downgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('is_onboarded')
