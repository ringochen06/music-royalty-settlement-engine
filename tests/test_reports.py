"""Tests for the Reports module."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database import Base
from src.ingestion.models import IngestionJob, JobStatus, StreamingRecord
from src.ledger.service import LedgerService
from src.parties.models import PartyType
from src.parties.service import PartyService
from src.contracts.models import ContractStatus
from src.contracts.service import ContractService
from src.reports.service import ReportsService
from src.settlement.service import SettlementService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def ledger_service(db_session) -> LedgerService:
    svc = LedgerService(db_session)
    svc.seed_standard_accounts()
    return svc


@pytest.fixture
def party_service(db_session) -> PartyService:
    return PartyService(db_session)


@pytest.fixture
def contract_service(db_session) -> ContractService:
    return ContractService(db_session)


@pytest.fixture
def settlement_service(db_session) -> SettlementService:
    return SettlementService(db_session)


@pytest.fixture
def reports_service(db_session) -> ReportsService:
    return ReportsService(db_session)


@pytest.fixture
def parties(party_service, db_session):
    artist = party_service.create_party(name="Artist A", party_type=PartyType.ARTIST)
    label = party_service.create_party(name="Label B", party_type=PartyType.LABEL)
    db_session.commit()
    return {"artist": artist, "label": label}


def _make_job(db: Session, statement_id: str = "STMT-001", records: list[dict] | None = None) -> IngestionJob:
    job = IngestionJob(
        statement_id=statement_id,
        file_hash="abc123" + statement_id,
        file_name="statement.csv",
        statement_date=date(2026, 1, 31),
        status=JobStatus.COMPLETED,
        total_records=len(records or []),
        total_revenue_micros=sum(r["revenue_micros"] for r in (records or [])),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    for r in records or []:
        rec = StreamingRecord(
            job_id=job.id,
            track_id=r["track_id"],
            track_name=r.get("track_name", r["track_id"]),
            artist_name=r.get("artist_name", "Artist"),
            streams=r.get("streams", 100),
            revenue_micros=r["revenue_micros"],
            statement_date=date(2026, 1, 31),
        )
        db.add(rec)
    db.flush()
    return job


def _make_active_contract(db, contract_service, track_id, splits):
    contract = contract_service.create_contract(
        name=f"Contract for {track_id}",
        track_id=track_id,
        effective_date=date(2025, 1, 1),
        expiry_date=None,
        splits=splits,
    )
    contract_service.activate_contract(contract.id)
    db.flush()
    return contract


# ---------------------------------------------------------------------------
# Trial Balance
# ---------------------------------------------------------------------------


class TestTrialBalance:
    def test_returns_balanced_on_empty_ledger(self, reports_service, ledger_service):
        result = reports_service.get_trial_balance()
        assert result["is_balanced"] is True
        assert result["total_debits_micros"] == 0
        assert result["total_credits_micros"] == 0
        assert len(result["line_items"]) > 0  # standard accounts seeded

    def test_balances_after_journal_entry(self, reports_service, ledger_service):
        ar = ledger_service.get_account_by_number("1100")
        rev = ledger_service.get_account_by_number("4100")
        from src.ledger.service import PostingLine
        from src.common.money import Money
        ledger_service.create_journal_entry(
            occurred_at=datetime.now(timezone.utc),
            description="Test entry",
            postings=[
                PostingLine(account_id=ar.id, amount=Money(micros=1_000_000), is_debit=True),
                PostingLine(account_id=rev.id, amount=Money(micros=1_000_000), is_debit=False),
            ],
        )
        result = reports_service.get_trial_balance()
        assert result["is_balanced"] is True
        assert result["total_debits_micros"] == 1_000_000
        assert result["total_credits_micros"] == 1_000_000


# ---------------------------------------------------------------------------
# Account Balances
# ---------------------------------------------------------------------------


class TestAccountBalances:
    def test_returns_all_accounts(self, reports_service, ledger_service):
        report = reports_service.get_account_balances()
        assert len(report.accounts) > 0

    def test_balances_zero_on_empty_ledger(self, reports_service, ledger_service):
        report = reports_service.get_account_balances()
        assert all(a.balance_micros == 0 for a in report.accounts)
        assert report.total_assets_micros == 0
        assert report.total_revenue_micros == 0

    def test_reflects_posted_entries(self, reports_service, ledger_service):
        ar = ledger_service.get_account_by_number("1100")
        rev = ledger_service.get_account_by_number("4100")
        from src.ledger.service import PostingLine
        from src.common.money import Money
        ledger_service.create_journal_entry(
            occurred_at=datetime.now(timezone.utc),
            description="Revenue entry",
            postings=[
                PostingLine(account_id=ar.id, amount=Money(micros=5_000_000), is_debit=True),
                PostingLine(account_id=rev.id, amount=Money(micros=5_000_000), is_debit=False),
            ],
        )
        report = reports_service.get_account_balances()
        ar_row = next(a for a in report.accounts if a.account_number == "1100")
        rev_row = next(a for a in report.accounts if a.account_number == "4100")
        assert ar_row.balance_micros == 5_000_000
        assert rev_row.balance_micros == 5_000_000
        assert ar_row.balance_dollars == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Settlement Summary
# ---------------------------------------------------------------------------


class TestSettlementSummary:
    def test_summary_includes_party_totals(
        self, db_session, reports_service, ledger_service, party_service, contract_service, settlement_service, parties
    ):
        artist = parties["artist"]
        label = parties["label"]
        job = _make_job(db_session, records=[
            {"track_id": "T1", "track_name": "Song A", "revenue_micros": 10_000_000},
        ])
        _make_active_contract(db_session, contract_service, "T1", [
            {"party_id": artist.id, "share_bps": 7000},
            {"party_id": label.id, "share_bps": 3000},
        ])
        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        report = reports_service.get_settlement_summary(run.id)
        assert report.run_id == run.id
        assert report.statement_id == "STMT-001"
        assert len(report.party_totals) == 2
        # Artist gets 70% of net, label gets 30%
        party_ids = {str(pt.party_id) for pt in report.party_totals}
        assert str(artist.id) in party_ids
        assert str(label.id) in party_ids
        total_party = sum(pt.total_amount_micros for pt in report.party_totals)
        assert total_party == run.total_net_micros

    def test_summary_not_found(self, reports_service, ledger_service):
        from src.common.exceptions import SettlementRunNotFoundError
        with pytest.raises(SettlementRunNotFoundError):
            reports_service.get_settlement_summary(uuid4())

    def test_summary_unmatched_run(
        self, db_session, reports_service, ledger_service, settlement_service
    ):
        job = _make_job(db_session, records=[
            {"track_id": "UNMATCHED", "track_name": "No Contract", "revenue_micros": 5_000_000},
        ])
        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        report = reports_service.get_settlement_summary(run.id)
        assert report.unmatched_tracks == 1
        assert report.party_totals == []  # no allocations for unmatched


# ---------------------------------------------------------------------------
# Party Statement
# ---------------------------------------------------------------------------


class TestPartyStatement:
    def test_statement_returns_line_items(
        self, db_session, reports_service, ledger_service, party_service, contract_service, settlement_service, parties
    ):
        artist = parties["artist"]
        job = _make_job(db_session, records=[
            {"track_id": "T1", "track_name": "Song A", "revenue_micros": 10_000_000},
            {"track_id": "T2", "track_name": "Song B", "revenue_micros": 4_000_000},
        ])
        _make_active_contract(db_session, contract_service, "T1", [
            {"party_id": artist.id, "share_bps": 10000},
        ])
        _make_active_contract(db_session, contract_service, "T2", [
            {"party_id": artist.id, "share_bps": 10000},
        ])
        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        report = reports_service.get_party_statement(artist.id)
        assert report.party_id == artist.id
        assert report.party_name == "Artist A"
        assert report.run_count == 1
        assert len(report.line_items) == 2
        assert report.total_amount_micros > 0

    def test_statement_no_settlements(self, db_session, reports_service, ledger_service, party_service):
        party = party_service.create_party(name="New Party", party_type=PartyType.ARTIST)
        db_session.commit()
        report = reports_service.get_party_statement(party.id)
        assert report.total_amount_micros == 0
        assert report.line_items == []
        assert report.run_count == 0

    def test_statement_party_not_found(self, reports_service, ledger_service):
        with pytest.raises(ValueError, match="not found"):
            reports_service.get_party_statement(uuid4())

    def test_statement_multiple_runs(
        self, db_session, reports_service, ledger_service, party_service, contract_service, settlement_service, parties
    ):
        artist = parties["artist"]
        for i, stmt_id in enumerate(["STMT-A", "STMT-B"]):
            track_id = f"T{i + 1}"
            job = _make_job(db_session, statement_id=stmt_id, records=[
                {"track_id": track_id, "track_name": f"Song {i + 1}", "revenue_micros": 6_000_000},
            ])
            _make_active_contract(db_session, contract_service, track_id, [
                {"party_id": artist.id, "share_bps": 10000},
            ])
            settlement_service.create_run(job_id=job.id)
            db_session.commit()

        report = reports_service.get_party_statement(artist.id)
        assert report.run_count == 2
        assert len(report.line_items) == 2
