"""Ingestion service - ETL pipeline with idempotency."""

import csv
from datetime import date, datetime, timezone
from io import StringIO
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.common.exceptions import DuplicateIngestionError, IngestionValidationError
from src.common.hashing import compute_string_hash
from src.common.money import Money
from src.ingestion.models import IngestionJob, JobStatus, StreamingRecord


class IngestionService:
    """Manages ETL pipeline for streaming data."""

    def __init__(self, db: Session):
        self.db = db

    def get_job(self, job_id: UUID) -> IngestionJob | None:
        return self.db.get(IngestionJob, job_id)

    def get_job_by_statement_id(self, statement_id: str) -> IngestionJob | None:
        stmt = select(IngestionJob).where(IngestionJob.statement_id == statement_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_jobs(
        self,
        status: JobStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[IngestionJob], int]:
        stmt = select(IngestionJob).order_by(IngestionJob.created_at.desc())

        if status:
            stmt = stmt.where(IngestionJob.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        jobs = list(self.db.execute(stmt).scalars().all())

        return jobs, total

    def list_records(
        self,
        job_id: UUID | None = None,
        track_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[StreamingRecord], int]:
        stmt = select(StreamingRecord).order_by(StreamingRecord.created_at.desc())

        if job_id:
            stmt = stmt.where(StreamingRecord.job_id == job_id)
        if track_id:
            stmt = stmt.where(StreamingRecord.track_id == track_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        records = list(self.db.execute(stmt).scalars().all())

        return records, total

    def create_job(
        self,
        statement_id: str,
        file_name: str,
        statement_date: date,
        file_content: str,
    ) -> IngestionJob:
        """Create and process an ingestion job.

        Args:
            statement_id: Business identifier for idempotency
            file_name: Original file name
            statement_date: Statement period date
            file_content: CSV content as string

        Returns:
            Created IngestionJob

        Raises:
            DuplicateIngestionError: If statement_id already exists
            IngestionValidationError: If CSV validation fails
        """
        file_hash = compute_string_hash(file_content)

        # Check for duplicate statement_id (primary idempotency key)
        existing_job = self.get_job_by_statement_id(statement_id)
        if existing_job:
            raise DuplicateIngestionError(
                message=f"Statement {statement_id} already ingested",
                statement_id=statement_id,
                existing_job_id=str(existing_job.id),
            )

        # Check for duplicate file_hash (secondary protection)
        stmt = select(IngestionJob).where(IngestionJob.file_hash == file_hash)
        duplicate_hash_job = self.db.execute(stmt).scalar_one_or_none()
        if duplicate_hash_job:
            raise DuplicateIngestionError(
                message=f"File with same content already ingested: {duplicate_hash_job.statement_id}",
                statement_id=statement_id,
                existing_job_id=str(duplicate_hash_job.id),
            )

        job = IngestionJob(
            statement_id=statement_id,
            file_hash=file_hash,
            file_name=file_name,
            statement_date=statement_date,
            status=JobStatus.PENDING,
        )
        self.db.add(job)
        self.db.flush()

        try:
            self._process_job(job, file_content)
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self.db.flush()
            raise

        return job

    def _process_job(self, job: IngestionJob, file_content: str) -> None:
        """Process CSV content and create streaming records."""
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        self.db.flush()

        records_data = self._parse_csv(file_content, job.statement_date)

        for record_data in records_data:
            record = StreamingRecord(
                job_id=job.id,
                **record_data,
            )
            self.db.add(record)

        job.total_records = len(records_data)
        job.total_revenue_micros = sum(r["revenue_micros"] for r in records_data)
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        self.db.flush()

    def _parse_csv(self, file_content: str, statement_date: date) -> list[dict]:
        """Parse CSV content and validate format.

        Expected CSV format:
        track_id,track_name,artist_name,streams,revenue_dollars

        Returns:
            List of record dictionaries

        Raises:
            IngestionValidationError: If CSV validation fails
        """
        errors = []
        records = []

        try:
            reader = csv.DictReader(StringIO(file_content))
            required_fields = {"track_id", "track_name", "artist_name", "streams", "revenue_dollars"}

            if not reader.fieldnames:
                raise IngestionValidationError("CSV file is empty", errors=[])

            missing_fields = required_fields - set(reader.fieldnames)
            if missing_fields:
                raise IngestionValidationError(
                    f"Missing required CSV columns: {missing_fields}",
                    errors=[{"error": "missing_columns", "fields": list(missing_fields)}],
                )

            for i, row in enumerate(reader, start=2):  # Start at 2 to account for header
                try:
                    track_id = row["track_id"].strip()
                    track_name = row["track_name"].strip()
                    artist_name = row["artist_name"].strip()
                    streams = int(row["streams"])
                    revenue_dollars = row["revenue_dollars"].strip()

                    if not track_id or not track_name or not artist_name:
                        errors.append({
                            "row": i,
                            "error": "empty_required_field",
                            "fields": [k for k, v in [
                                ("track_id", track_id),
                                ("track_name", track_name),
                                ("artist_name", artist_name),
                            ] if not v],
                        })
                        continue

                    if streams <= 0:
                        errors.append({
                            "row": i,
                            "error": "invalid_streams",
                            "value": streams,
                        })
                        continue

                    revenue_money = Money.from_dollars(revenue_dollars)
                    if revenue_money.micros <= 0:
                        errors.append({
                            "row": i,
                            "error": "invalid_revenue",
                            "value": revenue_dollars,
                        })
                        continue

                    records.append({
                        "track_id": track_id,
                        "track_name": track_name,
                        "artist_name": artist_name,
                        "streams": streams,
                        "revenue_micros": revenue_money.micros,
                        "statement_date": statement_date,
                    })

                except (ValueError, KeyError) as e:
                    errors.append({
                        "row": i,
                        "error": "parsing_error",
                        "message": str(e),
                    })

        except csv.Error as e:
            raise IngestionValidationError(f"CSV parsing error: {e}", errors=[])

        if errors:
            raise IngestionValidationError(
                f"CSV validation failed with {len(errors)} errors",
                errors=errors,
            )

        if not records:
            raise IngestionValidationError("No valid records found in CSV", errors=[])

        return records