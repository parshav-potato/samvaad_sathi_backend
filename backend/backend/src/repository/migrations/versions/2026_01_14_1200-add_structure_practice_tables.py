"""add structure practice tables

Revision ID: structure_practice_001
Revises: pronunciation_practice_001
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'structure_practice_001'
down_revision = 'pronunciation_practice_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create structure_practice table
    op.create_table(
        'structure_practice',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=True),
        sa.Column('track', sa.String(length=64), nullable=False),
        sa.Column('questions', JSONB, nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_structure_practice_user_id'),
        'structure_practice',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_structure_practice_interview_id'),
        'structure_practice',
        ['interview_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_structure_practice_track'),
        'structure_practice',
        ['track'],
        unique=False,
    )
    op.create_index(
        op.f('ix_structure_practice_status'),
        'structure_practice',
        ['status'],
        unique=False,
    )
    
    # Create structure_practice_answer table
    op.create_table(
        'structure_practice_answer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('practice_id', sa.Integer(), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('analysis_result', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['practice_id'], ['structure_practice.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_structure_practice_answer_practice_id'),
        'structure_practice_answer',
        ['practice_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_structure_practice_answer_question_index'),
        'structure_practice_answer',
        ['question_index'],
        unique=False,
    )


def downgrade() -> None:
    # Drop structure_practice_answer table
    op.drop_index(op.f('ix_structure_practice_answer_question_index'), table_name='structure_practice_answer')
    op.drop_index(op.f('ix_structure_practice_answer_practice_id'), table_name='structure_practice_answer')
    op.drop_table('structure_practice_answer')
    
    # Drop structure_practice table
    op.drop_index(op.f('ix_structure_practice_status'), table_name='structure_practice')
    op.drop_index(op.f('ix_structure_practice_track'), table_name='structure_practice')
    op.drop_index(op.f('ix_structure_practice_interview_id'), table_name='structure_practice')
    op.drop_index(op.f('ix_structure_practice_user_id'), table_name='structure_practice')
    op.drop_table('structure_practice')
