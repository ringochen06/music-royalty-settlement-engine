"""Tests for the ingestion module."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.common.exceptions import DuplicateIngestionError, IngestionValidationError
from src.database import Base
from src.ingestion.models import JobStatus
from src.ingestion.service import IngestionService


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def ingestion_service(db_session) -> IngestionService:
    return IngestionService(db_session)


# Sample CSV data
VALID_CSV = """track_id,track_name,artist_name,streams,revenue_dollars
TRACK-001,Song A,Artist 1,1000,10.50
TRACK-002,Song B,Artist 2,2500,25.75
TRACK-003,Song C,Artist 1,500,5.25"""

INVALID_CSV_MISSING_COLUMN = """track_id,track_name,streams,revenue_dollars
TRACK-001,Song A,1000,10.50"""

INVALID_CSV_NEGATIVE_STREAMS = """track_id,track_name,artist_name,streams,revenue_dollars
TRACK-001,Song A,Artist 1,-100,10.50"""

INVALID_CSV_EMPTY_REQUIRED = """track_id,track_name,artist_name,streams,revenue_dollars
,Song A,Artist 1,1000,10.50"""


class TestJobCreation:

    def test_create_job_with_valid_csv(self, ingestion_service, db_session):
        job = ingestion_service.create_job(
            statement_id="STMT-001",
            file_name="statement_2026_01.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        assert job.statement_id == "STMT-001"
        assert job.status == JobStatus.COMPLETED
        assert job.total_records == 3
        assert job.total_revenue_micros == 41_500_000  # $41.50 in micros
        assert len(job.records) == 3

    def test_create_job_calculates_file_hash(self, ingestion_service, db_session):
        job = ingestion_service.create_job(
            statement_id="STMT-002",
            file_name="test.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        assert len(job.file_hash) == 64  # SHA-256 hex digest length

    def test_duplicate_statement_id_raises(self, ingestion_service, db_session):
        ingestion_service.create_job(
            statement_id="STMT-DUP",
            file_name="first.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        with pytest.raises(DuplicateIngestionError) as exc:
            ingestion_service.create_job(
                statement_id="STMT-DUP",
                file_name="second.csv",
                statement_date=date(2026, 1, 31),
                file_content=VALID_CSV,
            )

        assert "STMT-DUP" in str(exc.value)

    def test_duplicate_file_hash_raises(self, ingestion_service, db_session):
        ingestion_service.create_job(
            statement_id="STMT-003",
            file_name="first.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        with pytest.raises(DuplicateIngestionError) as exc:
            ingestion_service.create_job(
                statement_id="STMT-004",
                file_name="second.csv",
                statement_date=date(2026, 1, 31),
                file_content=VALID_CSV,  # Same content
            )

        assert "same content" in str(exc.value)

    def test_invalid_csv_missing_column(self, ingestion_service):
        with pytest.raises(IngestionValidationError) as exc:
            ingestion_service.create_job(
                statement_id="STMT-005",
                file_name="bad.csv",
                statement_date=date(2026, 1, 31),
                file_content=INVALID_CSV_MISSING_COLUMN,
            )

        assert "Missing required CSV columns" in str(exc.value)

    def test_invalid_csv_negative_streams(self, ingestion_service, db_session):
        with pytest.raises(IngestionValidationError) as exc:
            ingestion_service.create_job(
                statement_id="STMT-006",
                file_name="negative.csv",
                statement_date=date(2026, 1, 31),
                file_content=INVALID_CSV_NEGATIVE_STREAMS,
            )

        assert "validation failed" in str(exc.value)
        assert exc.value.errors[0]["error"] == "invalid_streams"

    def test_invalid_csv_empty_required_field(self, ingestion_service):
        with pytest.raises(IngestionValidationError) as exc:
            ingestion_service.create_job(
                statement_id="STMT-007",
                file_name="empty.csv",
                statement_date=date(2026, 1, 31),
                file_content=INVALID_CSV_EMPTY_REQUIRED,
            )

        assert "validation failed" in str(exc.value)

    def test_job_failure_sets_error_message(self, ingestion_service, db_session):
        try:
            ingestion_service.create_job(
                statement_id="STMT-008",
                file_name="bad.csv",
                statement_date=date(2026, 1, 31),
                file_content=INVALID_CSV_MISSING_COLUMN,
            )
        except IngestionValidationError:
            pass

        db_session.commit()
        job = ingestion_service.get_job_by_statement_id("STMT-008")
        assert job.status == JobStatus.FAILED
        assert job.error_message is not None


class TestJobRetrieval:

    def test_get_job(self, ingestion_service, db_session):
        job = ingestion_service.create_job(
            statement_id="STMT-010",
            file_name="test.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        found = ingestion_service.get_job(job.id)
        assert found is not None
        assert found.statement_id == "STMT-010"

    def test_get_job_by_statement_id(self, ingestion_service, db_session):
        ingestion_service.create_job(
            statement_id="STMT-011",
            file_name="test.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        found = ingestion_service.get_job_by_statement_id("STMT-011")
        assert found is not None
        assert found.statement_id == "STMT-011"

    def test_get_nonexistent_job_by_statement_id(self, ingestion_service):
        found = ingestion_service.get_job_by_statement_id("NONEXISTENT")
        assert found is None


class TestJobListing:

    def test_list_all_jobs(self, ingestion_service, db_session):
        for i in range(3):
            # Use unique CSV content for each job to avoid duplicate hash
            csv_content = f"""track_id,track_name,artist_name,streams,revenue_dollars
TRACK-{i}01,Song A,Artist 1,1000,10.50
TRACK-{i}02,Song B,Artist 2,2500,25.75"""
            ingestion_service.create_job(
                statement_id=f"STMT-{i}",
                file_name=f"file{i}.csv",
                statement_date=date(2026, 1, 31),
                file_content=csv_content,
            )
        db_session.commit()

        jobs, total = ingestion_service.list_jobs()
        assert total == 3

    def test_filter_by_status(self, ingestion_service, db_session):
        ingestion_service.create_job(
            statement_id="STMT-COMPLETE",
            file_name="good.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )

        try:
            ingestion_service.create_job(
                statement_id="STMT-FAILED",
                file_name="bad.csv",
                statement_date=date(2026, 1, 31),
                file_content=INVALID_CSV_MISSING_COLUMN,
            )
        except IngestionValidationError:
            pass

        db_session.commit()

        completed, _ = ingestion_service.list_jobs(status=JobStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].statement_id == "STMT-COMPLETE"

        failed, _ = ingestion_service.list_jobs(status=JobStatus.FAILED)
        assert len(failed) == 1
        assert failed[0].statement_id == "STMT-FAILED"

    def test_pagination(self, ingestion_service, db_session):
        for i in range(5):
            # Use unique CSV content for each job to avoid duplicate hash
            csv_content = f"""track_id,track_name,artist_name,streams,revenue_dollars
TRACK-P{i}1,Song A,Artist 1,{1000 + i},10.50
TRACK-P{i}2,Song B,Artist 2,2500,25.75"""
            ingestion_service.create_job(
                statement_id=f"STMT-P{i}",
                file_name=f"file{i}.csv",
                statement_date=date(2026, 1, 31),
                file_content=csv_content,
            )
        db_session.commit()

        jobs, total = ingestion_service.list_jobs(page=1, page_size=2)
        assert total == 5
        assert len(jobs) == 2


class TestRecordListing:

    def test_list_all_records(self, ingestion_service, db_session):
        job = ingestion_service.create_job(
            statement_id="STMT-REC",
            file_name="test.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        records, total = ingestion_service.list_records()
        assert total == 3

    def test_filter_by_job_id(self, ingestion_service, db_session):
        csv_content_1 = """track_id,track_name,artist_name,streams,revenue_dollars
TRACK-J101,Song A,Artist 1,1000,10.50
TRACK-J102,Song B,Artist 2,2500,25.75
TRACK-J103,Song C,Artist 1,500,5.25"""
        csv_content_2 = """track_id,track_name,artist_name,streams,revenue_dollars
TRACK-J201,Song D,Artist 3,1500,15.00
TRACK-J202,Song E,Artist 4,3000,30.00
TRACK-J203,Song F,Artist 3,750,7.50"""
        job1 = ingestion_service.create_job(
            statement_id="STMT-J1",
            file_name="file1.csv",
            statement_date=date(2026, 1, 31),
            file_content=csv_content_1,
        )
        ingestion_service.create_job(
            statement_id="STMT-J2",
            file_name="file2.csv",
            statement_date=date(2026, 1, 31),
            file_content=csv_content_2,
        )
        db_session.commit()

        records, total = ingestion_service.list_records(job_id=job1.id)
        assert total == 3
        assert all(r.job_id == job1.id for r in records)

    def test_filter_by_track_id(self, ingestion_service, db_session):
        ingestion_service.create_job(
            statement_id="STMT-T",
            file_name="test.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        records, total = ingestion_service.list_records(track_id="TRACK-001")
        assert total == 1
        assert records[0].track_id == "TRACK-001"


class TestCSVParsing:

    def test_parse_revenue_precision(self, ingestion_service, db_session):
        csv_with_fractional_cents = """track_id,track_name,artist_name,streams,revenue_dollars
TRACK-FRAC,Micro Payment,Artist X,1,0.0034"""

        job = ingestion_service.create_job(
            statement_id="STMT-FRAC",
            file_name="micro.csv",
            statement_date=date(2026, 1, 31),
            file_content=csv_with_fractional_cents,
        )
        db_session.commit()

        assert job.total_revenue_micros == 3400  # $0.0034 = 3400 micros
        assert job.records[0].revenue_micros == 3400

    def test_parse_preserves_track_metadata(self, ingestion_service, db_session):
        job = ingestion_service.create_job(
            statement_id="STMT-META",
            file_name="meta.csv",
            statement_date=date(2026, 1, 31),
            file_content=VALID_CSV,
        )
        db_session.commit()

        record = job.records[0]
        assert record.track_id == "TRACK-001"
        assert record.track_name == "Song A"
        assert record.artist_name == "Artist 1"
        assert record.streams == 1000
        assert record.statement_date == date(2026, 1, 31)