"""create_ingestion_tables

Revision ID: 3b4c5d6e7f8g
Revises: 2a3b4c5d6e7f
Create Date: 2026-02-07 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8g'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ingestion_jobs table
    op.create_table('ingestion_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('statement_id', sa.String(length=100), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
                                     name='job_status'), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('total_revenue_micros', sa.BigInteger(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_job_statement_id', 'ingestion_jobs', ['statement_id'], unique=True)
    op.create_index('idx_job_file_hash', 'ingestion_jobs', ['file_hash'])
    op.create_index('idx_job_status', 'ingestion_jobs', ['status'])
    op.create_index('idx_job_statement_date', 'ingestion_jobs', ['statement_date'])

    # Create streaming_records table
    op.create_table('streaming_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('track_id', sa.String(length=100), nullable=False),
        sa.Column('track_name', sa.String(length=255), nullable=False),
        sa.Column('artist_name', sa.String(length=255), nullable=False),
        sa.Column('streams', sa.Integer(), nullable=False),
        sa.Column('revenue_micros', sa.BigInteger(), nullable=False),
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['ingestion_jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_record_job', 'streaming_records', ['job_id'])
    op.create_index('idx_record_track', 'streaming_records', ['track_id'])
    op.create_index('idx_record_statement_date', 'streaming_records', ['statement_date'])


def downgrade() -> None:
    op.drop_index('idx_record_statement_date', table_name='streaming_records')
    op.drop_index('idx_record_track', table_name='streaming_records')
    op.drop_index('idx_record_job', table_name='streaming_records')
    op.drop_table('streaming_records')
    op.drop_index('idx_job_statement_date', table_name='ingestion_jobs')
    op.drop_index('idx_job_status', table_name='ingestion_jobs')
    op.drop_index('idx_job_file_hash', table_name='ingestion_jobs')
    op.drop_index('idx_job_statement_id', table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')