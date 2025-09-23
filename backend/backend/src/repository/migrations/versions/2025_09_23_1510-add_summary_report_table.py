"""create summary_report table

Revision ID: 1f2e3d4c5b6a
Revises: b1a2c3d4e5f6
Create Date: 2025-09-23 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1f2e3d4c5b6a'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'summary_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('report_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_summary_report_interview_id'), 'summary_report', ['interview_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_summary_report_interview_id'), table_name='summary_report')
    op.drop_table('summary_report')
