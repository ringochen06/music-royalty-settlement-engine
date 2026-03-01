"""Settlement calculator - core revenue allocation logic."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.money import BasisPoints, Money, allocate_with_remainder
from src.contracts.service import ContractService
from src.ingestion.models import IngestionJob, StreamingRecord
from src.ledger.models import Account, AccountType
from src.ledger.service import LedgerService, PostingLine
from src.settlement.models import SettlementAllocation, SettlementLine, SettlementRun, SettlementStatus


class SettlementCalculator:
    """Processes an IngestionJob into journal entries and settlement lines."""

    def __init__(self, db: Session, ledger: LedgerService, contract_service: ContractService):
        self.db = db
        self.ledger = ledger
        self.contract_service = contract_service

    def calculate(self, run: SettlementRun, job: IngestionJob) -> SettlementRun:
        """Run settlement for all streaming records in the job.

        For each distinct track_id:
        1. Aggregate gross revenue
        2. Deduct platform fee
        3. Allocate net to parties (or suspense if no active contract)
        4. Write a balanced journal entry
        5. Record SettlementLine + SettlementAllocation rows
        """
        run.status = SettlementStatus.PROCESSING
        run.started_at = datetime.now(timezone.utc)
        self.db.flush()

        # Load system accounts needed for every entry
        ar_account = self.ledger.get_account_by_number("1100")       # Accounts Receivable
        fee_account = self.ledger.get_account_by_number("4000")       # Platform Fee Revenue
        clearing_account = self.ledger.get_account_by_number("2000")  # Revenue Clearing

        # Load all records for this job and group by track_id
        stmt = select(StreamingRecord).where(StreamingRecord.job_id == job.id)
        records = self.db.execute(stmt).scalars().all()

        tracks: dict[str, dict] = {}
        for rec in records:
            if rec.track_id not in tracks:
                tracks[rec.track_id] = {
                    "track_name": rec.track_name,
                    "gross_micros": 0,
                }
            tracks[rec.track_id]["gross_micros"] += rec.revenue_micros

        # Process each track
        total_gross = 0
        total_fee = 0
        total_net = 0
        total_unmatched = 0
        matched = 0
        unmatched = 0

        occurred_at = datetime.now(timezone.utc)

        for track_id, data in tracks.items():
            gross = Money(micros=data["gross_micros"])
            fee_bps = BasisPoints(value=run.platform_fee_bps)
            fee = fee_bps.apply_to(gross)
            net = gross - fee

            contract = self.contract_service.get_active_contract_for_track(track_id)

            if contract:
                # Build party splits for allocation
                splits = [
                    (str(split.party_id), BasisPoints(value=split.share_bps))
                    for split in contract.splits
                ]
                party_amounts = allocate_with_remainder(net, splits)

                # Build postings: DR AR, CR Fee, CR each party payable
                postings: list[PostingLine] = [
                    PostingLine(
                        account_id=ar_account.id,
                        amount=gross,
                        is_debit=True,
                        memo=f"Settlement: {track_id}",
                    ),
                    PostingLine(
                        account_id=fee_account.id,
                        amount=fee,
                        is_debit=False,
                        memo=f"Platform fee {run.platform_fee_bps} BPS: {track_id}",
                    ),
                ]
                allocations_data: list[dict] = []
                for split in contract.splits:
                    party_account = self._get_party_payable_account(split.party_id)
                    amount = party_amounts[str(split.party_id)]
                    postings.append(
                        PostingLine(
                            account_id=party_account.id,
                            amount=amount,
                            is_debit=False,
                            memo=f"Royalty: {track_id} ({split.share_bps} BPS)",
                        )
                    )
                    allocations_data.append({
                        "party_id": split.party_id,
                        "share_bps": split.share_bps,
                        "amount_micros": amount.micros,
                    })

                journal = self.ledger.create_journal_entry(
                    occurred_at=occurred_at,
                    description=f"Royalty settlement: {data['track_name']} ({track_id})",
                    postings=postings,
                    reference_type="settlement",
                    reference_id=run.id,
                )

                line = SettlementLine(
                    run_id=run.id,
                    track_id=track_id,
                    track_name=data["track_name"],
                    contract_id=contract.id,
                    gross_micros=gross.micros,
                    platform_fee_micros=fee.micros,
                    net_micros=net.micros,
                    is_unmatched=False,
                    journal_entry_id=journal.id,
                )
                self.db.add(line)
                self.db.flush()

                for alloc in allocations_data:
                    self.db.add(SettlementAllocation(
                        line_id=line.id,
                        party_id=alloc["party_id"],
                        share_bps=alloc["share_bps"],
                        amount_micros=alloc["amount_micros"],
                    ))

                matched += 1
                total_net += net.micros

            else:
                # No active contract — credit net to Revenue Clearing (suspense)
                postings = [
                    PostingLine(
                        account_id=ar_account.id,
                        amount=gross,
                        is_debit=True,
                        memo=f"Settlement (unmatched): {track_id}",
                    ),
                    PostingLine(
                        account_id=fee_account.id,
                        amount=fee,
                        is_debit=False,
                        memo=f"Platform fee {run.platform_fee_bps} BPS: {track_id}",
                    ),
                    PostingLine(
                        account_id=clearing_account.id,
                        amount=net,
                        is_debit=False,
                        memo=f"Suspense (no contract): {track_id}",
                    ),
                ]
                journal = self.ledger.create_journal_entry(
                    occurred_at=occurred_at,
                    description=f"Royalty settlement (unmatched): {data['track_name']} ({track_id})",
                    postings=postings,
                    reference_type="settlement",
                    reference_id=run.id,
                )

                line = SettlementLine(
                    run_id=run.id,
                    track_id=track_id,
                    track_name=data["track_name"],
                    contract_id=None,
                    gross_micros=gross.micros,
                    platform_fee_micros=fee.micros,
                    net_micros=net.micros,
                    is_unmatched=True,
                    journal_entry_id=journal.id,
                )
                self.db.add(line)

                unmatched += 1
                total_unmatched += net.micros

            total_gross += gross.micros
            total_fee += fee.micros

        # Write totals back to run
        run.total_tracks = len(tracks)
        run.matched_tracks = matched
        run.unmatched_tracks = unmatched
        run.total_gross_micros = total_gross
        run.total_platform_fee_micros = total_fee
        run.total_net_micros = total_net
        run.total_unmatched_micros = total_unmatched
        run.status = SettlementStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        self.db.flush()

        return run

    def _get_party_payable_account(self, party_id: UUID) -> Account:
        """Find the LIABILITY account auto-created for this party."""
        stmt = select(Account).where(
            Account.party_id == party_id,
            Account.account_type == AccountType.LIABILITY,
        )
        account = self.db.execute(stmt).scalar_one_or_none()
        if not account:
            raise ValueError(f"No payable account found for party {party_id}")
        return account
