"""Tests for the settlement module."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.exceptions import DuplicateSettlementError, IngestionJobNotFoundError
from src.database import Base
from src.ingestion.models import IngestionJob, JobStatus, StreamingRecord
from src.ledger.service import LedgerService
from src.parties.models import PartyType
from src.parties.service import PartyService
from src.contracts.models import ContractStatus
from src.contracts.service import ContractService
from src.settlement.models import SettlementStatus
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
def parties(party_service, db_session):
    artist = party_service.create_party(name="Artist", party_type=PartyType.ARTIST)
    label = party_service.create_party(name="Label", party_type=PartyType.LABEL)
    db_session.commit()
    return {"artist": artist, "label": label}


def _make_job(db: Session, statement_id: str = "STMT-001", records: list[dict] | None = None) -> IngestionJob:
    """Helper: create a COMPLETED IngestionJob with streaming records."""
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

    for r in (records or []):
        db.add(StreamingRecord(
            job_id=job.id,
            track_id=r["track_id"],
            track_name=r.get("track_name", r["track_id"]),
            artist_name=r.get("artist_name", "Artist"),
            streams=r.get("streams", 1000),
            revenue_micros=r["revenue_micros"],
            statement_date=date(2026, 1, 31),
        ))
    db.commit()
    return job


def _make_active_contract(contract_service, parties, track_id, db_session):
    """Helper: create an ACTIVE contract for a track with 50/50 split."""
    contract = contract_service.create_contract(
        name=f"Contract {track_id}",
        track_id=track_id,
        effective_date=date(2025, 1, 1),
        splits=[
            {"party_id": parties["artist"].id, "share_bps": 5000, "role": "artist"},
            {"party_id": parties["label"].id, "share_bps": 5000, "role": "label"},
        ],
    )
    contract_service.activate_contract(contract.id)
    db_session.commit()
    return contract


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuccessfulSettlement:

    def test_single_track_matched(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Single track with an active contract settles correctly."""
        _make_active_contract(contract_service, parties, "TRACK-001", db_session)
        # $10.00 gross
        job = _make_job(db_session, records=[
            {"track_id": "TRACK-001", "track_name": "Song A", "revenue_micros": 10_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        assert run.status == SettlementStatus.COMPLETED
        assert run.total_tracks == 1
        assert run.matched_tracks == 1
        assert run.unmatched_tracks == 0
        assert run.total_gross_micros == 10_000_000
        # Platform fee: 1500 BPS of 10_000_000 = 1_500_000
        assert run.total_platform_fee_micros == 1_500_000
        # Net = 8_500_000
        assert run.total_net_micros == 8_500_000
        assert run.total_unmatched_micros == 0

        assert len(run.lines) == 1
        line = run.lines[0]
        assert line.track_id == "TRACK-001"
        assert not line.is_unmatched
        assert line.gross_micros == 10_000_000
        assert line.platform_fee_micros == 1_500_000
        assert line.net_micros == 8_500_000
        assert line.journal_entry_id is not None

        # 50/50 split → each party gets 4_250_000
        assert len(line.allocations) == 2
        total_allocated = sum(a.amount_micros for a in line.allocations)
        assert total_allocated == 8_500_000

    def test_multi_track_settlement(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Multiple tracks each settle with their own contract entry."""
        _make_active_contract(contract_service, parties, "TRACK-A", db_session)
        _make_active_contract(contract_service, parties, "TRACK-B", db_session)

        job = _make_job(db_session, statement_id="STMT-MULTI", records=[
            {"track_id": "TRACK-A", "track_name": "Song A", "revenue_micros": 5_000_000},
            {"track_id": "TRACK-B", "track_name": "Song B", "revenue_micros": 3_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        assert run.status == SettlementStatus.COMPLETED
        assert run.total_tracks == 2
        assert run.matched_tracks == 2
        assert run.total_gross_micros == 8_000_000

    def test_aggregates_multiple_records_per_track(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Multiple records for the same track_id are aggregated into one line."""
        _make_active_contract(contract_service, parties, "TRACK-X", db_session)

        job = _make_job(db_session, statement_id="STMT-AGG", records=[
            {"track_id": "TRACK-X", "track_name": "Song X", "revenue_micros": 2_000_000},
            {"track_id": "TRACK-X", "track_name": "Song X", "revenue_micros": 3_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        assert run.total_tracks == 1  # Aggregated to 1 distinct track
        assert run.total_gross_micros == 5_000_000
        assert run.lines[0].gross_micros == 5_000_000


class TestUnmatchedTrack:

    def test_unmatched_track_goes_to_clearing(
        self, db_session, ledger_service, settlement_service
    ):
        """Track with no active contract is flagged as unmatched and credited to clearing."""
        job = _make_job(db_session, statement_id="STMT-UNMATCH", records=[
            {"track_id": "NO-CONTRACT", "track_name": "Mystery Song", "revenue_micros": 6_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        assert run.status == SettlementStatus.COMPLETED
        assert run.unmatched_tracks == 1
        assert run.matched_tracks == 0
        assert run.total_unmatched_micros == 5_100_000  # net after 15% fee
        assert run.total_net_micros == 0

        line = run.lines[0]
        assert line.is_unmatched
        assert line.contract_id is None
        assert len(line.allocations) == 0


class TestIdempotency:

    def test_duplicate_run_rejected(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Settling the same job twice raises DuplicateSettlementError."""
        _make_active_contract(contract_service, parties, "TRACK-DUP", db_session)
        job = _make_job(db_session, statement_id="STMT-DUP", records=[
            {"track_id": "TRACK-DUP", "track_name": "Dup Song", "revenue_micros": 1_000_000},
        ])

        settlement_service.create_run(job_id=job.id)
        db_session.commit()

        with pytest.raises(DuplicateSettlementError):
            settlement_service.create_run(job_id=job.id)


class TestValidation:

    def test_job_not_found_raises(self, db_session, settlement_service):
        with pytest.raises(IngestionJobNotFoundError):
            settlement_service.create_run(job_id=uuid4())

    def test_job_not_completed_raises(self, db_session, settlement_service):
        job = IngestionJob(
            statement_id="STMT-PENDING",
            file_hash="xyz",
            file_name="f.csv",
            statement_date=date(2026, 1, 31),
            status=JobStatus.PENDING,
            total_records=0,
            total_revenue_micros=0,
        )
        db_session.add(job)
        db_session.commit()

        with pytest.raises(ValueError, match="COMPLETED"):
            settlement_service.create_run(job_id=job.id)


class TestPlatformFeeCalculation:

    def test_platform_fee_is_correct_bps(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Platform fee = platform_fee_bps / 10000 of gross."""
        _make_active_contract(contract_service, parties, "TRACK-FEE", db_session)
        job = _make_job(db_session, statement_id="STMT-FEE", records=[
            {"track_id": "TRACK-FEE", "track_name": "Fee Song", "revenue_micros": 10_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        # Default PLATFORM_FEE_BPS = 1500 (15%)
        expected_fee = (10_000_000 * run.platform_fee_bps) // 10_000
        assert run.total_platform_fee_micros == expected_fee

    def test_platform_fee_bps_is_snapshotted(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """platform_fee_bps is stored on the run for audit trail."""
        _make_active_contract(contract_service, parties, "TRACK-SNAP", db_session)
        job = _make_job(db_session, statement_id="STMT-SNAP", records=[
            {"track_id": "TRACK-SNAP", "track_name": "Snap", "revenue_micros": 1_000_000},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        assert run.platform_fee_bps == 1500  # from settings


class TestMoneyAllocationPrecision:

    def test_allocation_total_equals_net_exactly(
        self, db_session, ledger_service, parties, contract_service, settlement_service
    ):
        """Sum of party allocations must equal net_micros exactly (largest remainder method)."""
        _make_active_contract(contract_service, parties, "TRACK-PREC", db_session)
        # Use an odd amount to stress the remainder distribution
        job = _make_job(db_session, statement_id="STMT-PREC", records=[
            {"track_id": "TRACK-PREC", "track_name": "Precision", "revenue_micros": 7_777_777},
        ])

        run = settlement_service.create_run(job_id=job.id)
        db_session.commit()

        line = run.lines[0]
        total_allocated = sum(a.amount_micros for a in line.allocations)
        assert total_allocated == line.net_micros, (
            f"Allocation sum {total_allocated} != net {line.net_micros}"
        )
