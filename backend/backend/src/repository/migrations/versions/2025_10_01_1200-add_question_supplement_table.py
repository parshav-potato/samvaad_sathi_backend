"""add question supplement table

Revision ID: 3a2c1f4b8b10
Revises: 8f5f6d27c6e0
Create Date: 2025-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a2c1f4b8b10'
down_revision = '8f5f6d27c6e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'question_supplement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_question_id', sa.Integer(), nullable=False),
        sa.Column('supplement_type', sa.String(length=32), nullable=False),
        sa.Column('format', sa.String(length=32), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_question_id'], ['interview_question.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_question_id')
    )
    op.create_index(
        op.f('ix_question_supplement_interview_question_id'),
        'question_supplement',
        ['interview_question_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_question_supplement_interview_question_id'), table_name='question_supplement')
    op.drop_table('question_supplement')

