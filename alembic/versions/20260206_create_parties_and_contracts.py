"""create_parties_and_contracts

Revision ID: 2a3b4c5d6e7f
Revises: 1bea294206ca
Create Date: 2026-02-06 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '1bea294206ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create parties table (no dependencies)
    op.create_table('parties',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('party_type', sa.Enum('ARTIST', 'LABEL', 'PRODUCER', 'PUBLISHER',
                                        'DISTRIBUTOR', 'SONGWRITER', name='party_type'),
                  nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', name='party_status'),
                  nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('external_id', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )
    op.create_index('idx_party_type', 'parties', ['party_type'])
    op.create_index('idx_party_status', 'parties', ['status'])
    op.create_index('idx_party_name', 'parties', ['name'])

    # 2. Create contracts table (no dependencies)
    op.create_table('contracts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('track_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'EXPIRED', 'TERMINATED',
                                     name='contract_status'), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_contract_status', 'contracts', ['status'])
    op.create_index('idx_contract_track', 'contracts', ['track_id'])
    op.create_index('idx_contract_dates', 'contracts', ['effective_date', 'expiry_date'])

    # 3. Create contract_splits table (depends on contracts + parties)
    op.create_table('contract_splits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('party_id', sa.UUID(), nullable=False),
        sa.Column('share_bps', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.CheckConstraint('share_bps > 0', name='positive_share'),
        sa.CheckConstraint('share_bps <= 10000', name='max_share'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['party_id'], ['parties.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_split_contract', 'contract_splits', ['contract_id'])
    op.create_index('idx_split_party', 'contract_splits', ['party_id'])

    # 4. Add FK on existing accounts.party_id -> parties.id
    op.create_foreign_key(
        'fk_accounts_party_id', 'accounts', 'parties', ['party_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_accounts_party_id', 'accounts', type_='foreignkey')
    op.drop_index('idx_split_party', table_name='contract_splits')
    op.drop_index('idx_split_contract', table_name='contract_splits')
    op.drop_table('contract_splits')
    op.drop_index('idx_contract_dates', table_name='contracts')
    op.drop_index('idx_contract_track', table_name='contracts')
    op.drop_index('idx_contract_status', table_name='contracts')
    op.drop_table('contracts')
    op.drop_index('idx_party_name', table_name='parties')
    op.drop_index('idx_party_status', table_name='parties')
    op.drop_index('idx_party_type', table_name='parties')
    op.drop_table('parties')
