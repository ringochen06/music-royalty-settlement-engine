"""Reports schemas - read-only response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.ledger.models import AccountType, NormalBalance


# ─── Account Balances ────────────────────────────────────────────────────────


class AccountBalanceRow(BaseModel):
    account_id: UUID
    account_number: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    balance_micros: int
    balance_dollars: float


class AccountBalancesReport(BaseModel):
    generated_at: datetime
    accounts: list[AccountBalanceRow]
    total_assets_micros: int
    total_liabilities_micros: int
    total_revenue_micros: int
    total_expenses_micros: int


# ─── Settlement Summary ───────────────────────────────────────────────────────


class SettlementSummaryPartyRow(BaseModel):
    party_id: UUID
    party_name: str
    party_type: str
    total_amount_micros: int
    track_count: int


class SettlementSummaryReport(BaseModel):
    run_id: UUID
    statement_id: str
    status: str
    platform_fee_bps: int
    generated_at: datetime
    total_tracks: int
    matched_tracks: int
    unmatched_tracks: int
    total_gross_micros: int
    total_platform_fee_micros: int
    total_net_micros: int
    total_unmatched_micros: int
    party_totals: list[SettlementSummaryPartyRow]


# ─── Party Statement ─────────────────────────────────────────────────────────


class PartyStatementLineItem(BaseModel):
    run_id: UUID
    statement_id: str
    track_id: str
    track_name: str
    share_bps: int
    amount_micros: int
    settlement_date: datetime


class PartyStatementReport(BaseModel):
    party_id: UUID
    party_name: str
    party_type: str
    generated_at: datetime
    from_date: datetime | None
    to_date: datetime | None
    line_items: list[PartyStatementLineItem]
    total_amount_micros: int
    run_count: int
