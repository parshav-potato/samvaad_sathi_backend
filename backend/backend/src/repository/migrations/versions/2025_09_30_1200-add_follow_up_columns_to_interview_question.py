"""add follow up columns to interview question

Revision ID: 8f5f6d27c6e0
Revises: 5152c4336536
Create Date: 2025-09-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f5f6d27c6e0'
down_revision = '5152c4336536'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('interview_question', sa.Column('is_follow_up', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('interview_question', sa.Column('parent_question_id', sa.Integer(), nullable=True))
    op.add_column('interview_question', sa.Column('follow_up_strategy', sa.String(length=64), nullable=True))
    op.create_index('ix_interview_question_is_follow_up', 'interview_question', ['is_follow_up'])
    op.create_index('ix_interview_question_parent_question_id', 'interview_question', ['parent_question_id'])
    op.create_foreign_key(
        'fk_interview_question_parent_question_id',
        'interview_question',
        'interview_question',
        ['parent_question_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.alter_column('interview_question', 'is_follow_up', server_default=None)


def downgrade() -> None:
    op.drop_constraint('fk_interview_question_parent_question_id', 'interview_question', type_='foreignkey')
    op.drop_index('ix_interview_question_parent_question_id', table_name='interview_question')
    op.drop_index('ix_interview_question_is_follow_up', table_name='interview_question')
    op.drop_column('interview_question', 'follow_up_strategy')
    op.drop_column('interview_question', 'parent_question_id')
    op.drop_column('interview_question', 'is_follow_up')

