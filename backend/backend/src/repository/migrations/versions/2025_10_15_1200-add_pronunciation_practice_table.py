"""add pronunciation practice table

Revision ID: pronunciation_practice_001
Revises: 3a2c1f4b8b10
Create Date: 2025-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'pronunciation_practice_001'
down_revision = '4c3d5c7aa1a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pronunciation_practice',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('words', JSONB, nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_pronunciation_practice_user_id'),
        'pronunciation_practice',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_pronunciation_practice_created_at'),
        'pronunciation_practice',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_pronunciation_practice_created_at'), table_name='pronunciation_practice')
    op.drop_index(op.f('ix_pronunciation_practice_user_id'), table_name='pronunciation_practice')
    op.drop_table('pronunciation_practice')
