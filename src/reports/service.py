"""Reports service - read-only aggregation queries."""

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.exceptions import SettlementRunNotFoundError
from src.ledger.models import AccountType
from src.ledger.service import LedgerService
from src.parties.models import Party
from src.reports.schemas import (
    AccountBalanceRow,
    AccountBalancesReport,
    PartyStatementLineItem,
    PartyStatementReport,
    SettlementSummaryPartyRow,
    SettlementSummaryReport,
)
from src.settlement.models import SettlementAllocation, SettlementLine, SettlementRun


class ReportsService:
    def __init__(self, db: Session):
        self.db = db
        self._ledger = LedgerService(db)

    # ─── Trial Balance ────────────────────────────────────────────────────────

    def get_trial_balance(self) -> dict:
        """Proxy to LedgerService.get_trial_balance()."""
        return self._ledger.get_trial_balance()

    # ─── Account Balances ─────────────────────────────────────────────────────

    def get_account_balances(self) -> AccountBalancesReport:
        accounts = self._ledger.list_accounts()
        rows: list[AccountBalanceRow] = []
        totals: dict[AccountType, int] = defaultdict(int)

        for account in accounts:
            balance = self._ledger.get_account_balance(account.id)
            micros = balance.micros
            totals[account.account_type] += micros
            rows.append(
                AccountBalanceRow(
                    account_id=account.id,
                    account_number=account.account_number,
                    account_name=account.name,
                    account_type=account.account_type,
                    normal_balance=account.normal_balance,
                    balance_micros=micros,
                    balance_dollars=micros / 1_000_000,
                )
            )

        return AccountBalancesReport(
            generated_at=datetime.now(timezone.utc),
            accounts=rows,
            total_assets_micros=totals[AccountType.ASSET],
            total_liabilities_micros=totals[AccountType.LIABILITY],
            total_revenue_micros=totals[AccountType.REVENUE],
            total_expenses_micros=totals[AccountType.EXPENSE],
        )

    # ─── Settlement Summary ───────────────────────────────────────────────────

    def get_settlement_summary(self, run_id: UUID) -> SettlementSummaryReport:
        run = self.db.get(SettlementRun, run_id)
        if not run:
            raise SettlementRunNotFoundError(run_id=str(run_id))

        # Aggregate allocations → party totals
        stmt = (
            select(SettlementAllocation)
            .join(SettlementLine, SettlementAllocation.line_id == SettlementLine.id)
            .where(SettlementLine.run_id == run_id)
        )
        allocations = list(self.db.execute(stmt).scalars().all())

        party_amounts: dict[UUID, int] = defaultdict(int)
        party_tracks: dict[UUID, set] = defaultdict(set)
        for alloc in allocations:
            party_amounts[alloc.party_id] += alloc.amount_micros
            party_tracks[alloc.party_id].add(alloc.line_id)

        # Fetch party names
        party_ids = list(party_amounts.keys())
        parties: dict[UUID, Party] = {}
        if party_ids:
            party_rows = list(
                self.db.execute(select(Party).where(Party.id.in_(party_ids))).scalars().all()
            )
            parties = {p.id: p for p in party_rows}

        party_totals = [
            SettlementSummaryPartyRow(
                party_id=pid,
                party_name=parties[pid].name if pid in parties else "Unknown",
                party_type=parties[pid].party_type.value if pid in parties else "unknown",
                total_amount_micros=amount,
                track_count=len(party_tracks[pid]),
            )
            for pid, amount in sorted(party_amounts.items(), key=lambda x: -x[1])
        ]

        return SettlementSummaryReport(
            run_id=run.id,
            statement_id=run.statement_id,
            status=run.status.value,
            platform_fee_bps=run.platform_fee_bps,
            generated_at=datetime.now(timezone.utc),
            total_tracks=run.total_tracks,
            matched_tracks=run.matched_tracks,
            unmatched_tracks=run.unmatched_tracks,
            total_gross_micros=run.total_gross_micros,
            total_platform_fee_micros=run.total_platform_fee_micros,
            total_net_micros=run.total_net_micros,
            total_unmatched_micros=run.total_unmatched_micros,
            party_totals=party_totals,
        )

    # ─── Party Statement ─────────────────────────────────────────────────────

    def get_party_statement(
        self,
        party_id: UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> PartyStatementReport:
        party = self.db.get(Party, party_id)
        if not party:
            raise ValueError(f"Party {party_id} not found")

        stmt = (
            select(SettlementAllocation, SettlementLine, SettlementRun)
            .join(SettlementLine, SettlementAllocation.line_id == SettlementLine.id)
            .join(SettlementRun, SettlementLine.run_id == SettlementRun.id)
            .where(SettlementAllocation.party_id == party_id)
        )
        if from_date:
            stmt = stmt.where(SettlementRun.created_at >= from_date)
        if to_date:
            stmt = stmt.where(SettlementRun.created_at <= to_date)
        stmt = stmt.order_by(SettlementRun.created_at.desc(), SettlementLine.track_id)

        rows = self.db.execute(stmt).all()

        line_items: list[PartyStatementLineItem] = []
        seen_runs: set[UUID] = set()
        total_micros = 0

        for alloc, line, run in rows:
            seen_runs.add(run.id)
            total_micros += alloc.amount_micros
            line_items.append(
                PartyStatementLineItem(
                    run_id=run.id,
                    statement_id=run.statement_id,
                    track_id=line.track_id,
                    track_name=line.track_name,
                    share_bps=alloc.share_bps,
                    amount_micros=alloc.amount_micros,
                    settlement_date=run.created_at,
                )
            )

        return PartyStatementReport(
            party_id=party.id,
            party_name=party.name,
            party_type=party.party_type.value,
            generated_at=datetime.now(timezone.utc),
            from_date=from_date,
            to_date=to_date,
            line_items=line_items,
            total_amount_micros=total_micros,
            run_count=len(seen_runs),
        )
