"""remove_account_table

Revision ID: 0db6df8cca11
Revises: add_core_models_20250826
Create Date: 2025-08-30 22:27:02.691293

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0db6df8cca11'
down_revision = 'add_core_models_20250826'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop account table since we've migrated to User-based auth
    op.drop_table('account')


def downgrade() -> None:
    # Recreate account table if needed (for rollback)
    op.create_table(
        'account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=64), nullable=False),
        sa.Column('_hashed_password', sa.String(length=1024), nullable=True),
        sa.Column('_hash_salt', sa.String(length=1024), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_logged_in', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
