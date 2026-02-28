"""add pacing practice session table

Revision ID: pacing_practice_001
Revises: structure_practice_002
Create Date: 2026-02-28 12:00:00.000000

Backward-compatibility notes
----------------------------
* Purely additive: only a new table is created. No existing table or column
  is modified, so rolling back to an older backend release against this
  schema is safe – the old code simply ignores the new table.
* status has a DB-level server_default so all INSERT paths (ORM or raw SQL)
  always produce a valid row.
* updated_at is maintained by a PostgreSQL BEFORE UPDATE trigger so that
  even raw-SQL UPDATEs (e.g. from an older backend release that somehow
  touches the table) keep the timestamp accurate.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'pacing_practice_001'
down_revision = 'structure_practice_002'
branch_labels = None
depends_on = None

# PostgreSQL trigger that auto-updates the updated_at column on every UPDATE.
_TRIGGER_FN_SQL = """
CREATE OR REPLACE FUNCTION set_pacing_practice_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_TRIGGER_SQL = """
CREATE TRIGGER trg_pacing_practice_session_updated_at
BEFORE UPDATE ON pacing_practice_session
FOR EACH ROW EXECUTE FUNCTION set_pacing_practice_session_updated_at();
"""

_DROP_TRIGGER_SQL = "DROP TRIGGER IF EXISTS trg_pacing_practice_session_updated_at ON pacing_practice_session;"
_DROP_TRIGGER_FN_SQL = "DROP FUNCTION IF EXISTS set_pacing_practice_session_updated_at();"


def upgrade() -> None:
    op.create_table(
        'pacing_practice_session',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_index', sa.Integer(), nullable=False),
        # server_default uses sa.text() so the SQL literal 'pending' is emitted,
        # not a bind-parameter placeholder. Matches the pattern in existing tables.
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('words_data', JSONB, nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('wpm', sa.Float(), nullable=True),
        sa.Column('pause_words_interval', sa.Float(), nullable=True),
        sa.Column('analysis_result', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pacing_practice_session_user_id', 'pacing_practice_session', ['user_id'])
    op.create_index('ix_pacing_practice_session_level', 'pacing_practice_session', ['level'])
    op.create_index('ix_pacing_practice_session_status', 'pacing_practice_session', ['status'])
    op.create_index('ix_pacing_practice_session_user_level', 'pacing_practice_session', ['user_id', 'level'])

    # DB-level trigger so updated_at is always accurate, regardless of whether
    # the update comes from the ORM, a Core statement, or a raw SQL query.
    op.execute(_TRIGGER_FN_SQL)
    op.execute(_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(_DROP_TRIGGER_SQL)
    op.execute(_DROP_TRIGGER_FN_SQL)
    op.drop_index('ix_pacing_practice_session_user_level', table_name='pacing_practice_session')
    op.drop_index('ix_pacing_practice_session_status', table_name='pacing_practice_session')
    op.drop_index('ix_pacing_practice_session_level', table_name='pacing_practice_session')
    op.drop_index('ix_pacing_practice_session_user_id', table_name='pacing_practice_session')
    op.drop_table('pacing_practice_session')
