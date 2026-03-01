"""Settlement service - orchestrates settlement runs."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.common.exceptions import (
    DuplicateSettlementError,
    IngestionJobNotFoundError,
    SettlementRunNotFoundError,
)
from src.config import settings
from src.contracts.service import ContractService
from src.ingestion.models import IngestionJob, JobStatus
from src.ledger.service import LedgerService
from src.settlement.calculator import SettlementCalculator
from src.settlement.models import SettlementLine, SettlementRun, SettlementStatus


class SettlementService:
    """Manages settlement runs against completed ingestion jobs."""

    def __init__(self, db: Session):
        self.db = db

    def create_run(self, job_id: UUID) -> SettlementRun:
        """Create and execute a settlement run for a completed ingestion job.

        Idempotent: raises DuplicateSettlementError if job_id already settled.
        """
        # Idempotency check
        existing = self._get_run_by_job_id(job_id)
        if existing:
            raise DuplicateSettlementError(
                message=f"Job {job_id} has already been settled",
                statement_id=existing.statement_id,
                existing_run_id=str(existing.id),
            )

        # Validate job exists and is ready
        job = self.db.get(IngestionJob, job_id)
        if not job:
            raise IngestionJobNotFoundError(job_id=str(job_id))
        if job.status != JobStatus.COMPLETED:
            raise ValueError(
                f"Cannot settle job with status '{job.status.value}'. Job must be COMPLETED."
            )

        run = SettlementRun(
            job_id=job_id,
            statement_id=job.statement_id,
            status=SettlementStatus.PENDING,
            platform_fee_bps=settings.platform_fee_bps,
        )
        self.db.add(run)
        self.db.flush()

        try:
            ledger = LedgerService(self.db)
            contract_service = ContractService(self.db)
            calculator = SettlementCalculator(self.db, ledger, contract_service)
            calculator.calculate(run, job)
        except Exception as e:
            run.status = SettlementStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            self.db.flush()
            raise

        return run

    def get_run(self, run_id: UUID) -> SettlementRun:
        run = self.db.get(SettlementRun, run_id)
        if not run:
            raise SettlementRunNotFoundError(run_id=str(run_id))
        return run

    def list_runs(
        self,
        status: SettlementStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SettlementRun], int]:
        stmt = select(SettlementRun).order_by(SettlementRun.created_at.desc())

        if status:
            stmt = stmt.where(SettlementRun.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        runs = list(self.db.execute(stmt).scalars().all())

        return runs, total

    def list_lines(
        self,
        run_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SettlementLine], int]:
        # Verify run exists
        self.get_run(run_id)

        stmt = (
            select(SettlementLine)
            .where(SettlementLine.run_id == run_id)
            .order_by(SettlementLine.track_id)
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        lines = list(self.db.execute(stmt).scalars().all())

        return lines, total

    def _get_run_by_job_id(self, job_id: UUID) -> SettlementRun | None:
        stmt = select(SettlementRun).where(SettlementRun.job_id == job_id)
        return self.db.execute(stmt).scalar_one_or_none()
