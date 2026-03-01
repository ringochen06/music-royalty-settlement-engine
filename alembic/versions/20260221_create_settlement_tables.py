"""create_settlement_tables

Revision ID: 4c5d6e7f8g9h
Revises: 3b4c5d6e7f8g
Create Date: 2026-02-21 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8g9h'
down_revision: Union[str, None] = '3b4c5d6e7f8g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create settlement_runs table
    op.create_table(
        'settlement_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('statement_id', sa.String(length=100), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'processing', 'completed', 'failed', name='settlement_status'),
            nullable=False,
        ),
        sa.Column('platform_fee_bps', sa.Integer(), nullable=False),
        sa.Column('total_tracks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_tracks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unmatched_tracks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_gross_micros', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_platform_fee_micros', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_net_micros', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_unmatched_micros', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['ingestion_jobs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )
    op.create_index('idx_run_job_id', 'settlement_runs', ['job_id'], unique=True)
    op.create_index('idx_run_status', 'settlement_runs', ['status'])
    op.create_index('idx_run_statement_id', 'settlement_runs', ['statement_id'])

    # Create settlement_lines table
    op.create_table(
        'settlement_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('track_id', sa.String(length=100), nullable=False),
        sa.Column('track_name', sa.String(length=255), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=True),
        sa.Column('gross_micros', sa.BigInteger(), nullable=False),
        sa.Column('platform_fee_micros', sa.BigInteger(), nullable=False),
        sa.Column('net_micros', sa.BigInteger(), nullable=False),
        sa.Column('is_unmatched', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('journal_entry_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['settlement_runs.id']),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_line_run', 'settlement_lines', ['run_id'])
    op.create_index('idx_line_track', 'settlement_lines', ['track_id'])

    # Create settlement_allocations table
    op.create_table(
        'settlement_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('line_id', sa.UUID(), nullable=False),
        sa.Column('party_id', sa.UUID(), nullable=False),
        sa.Column('share_bps', sa.Integer(), nullable=False),
        sa.Column('amount_micros', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['line_id'], ['settlement_lines.id']),
        sa.ForeignKeyConstraint(['party_id'], ['parties.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_alloc_line', 'settlement_allocations', ['line_id'])
    op.create_index('idx_alloc_party', 'settlement_allocations', ['party_id'])


def downgrade() -> None:
    op.drop_index('idx_alloc_party', table_name='settlement_allocations')
    op.drop_index('idx_alloc_line', table_name='settlement_allocations')
    op.drop_table('settlement_allocations')

    op.drop_index('idx_line_track', table_name='settlement_lines')
    op.drop_index('idx_line_run', table_name='settlement_lines')
    op.drop_table('settlement_lines')

    op.drop_index('idx_run_statement_id', table_name='settlement_runs')
    op.drop_index('idx_run_status', table_name='settlement_runs')
    op.drop_index('idx_run_job_id', table_name='settlement_runs')
    op.drop_table('settlement_runs')
    op.execute('DROP TYPE IF EXISTS settlement_status')
