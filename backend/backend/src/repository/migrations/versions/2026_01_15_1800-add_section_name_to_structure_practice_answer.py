"""add section_name to structure_practice_answer

Revision ID: structure_practice_002
Revises: structure_practice_001
Create Date: 2026-01-15 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'structure_practice_002'
down_revision = 'structure_practice_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add section_name column with a default value for existing rows
    op.add_column('structure_practice_answer', 
        sa.Column('section_name', sa.String(length=32), nullable=False, server_default='Complete')
    )
    
    # Remove the server default after adding the column (we only needed it for existing rows)
    op.alter_column('structure_practice_answer', 'section_name', server_default=None)


def downgrade() -> None:
    op.drop_column('structure_practice_answer', 'section_name')
