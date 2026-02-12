"""Ingestion models - ETL pipeline for streaming data."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(Base):
    """ETL job for importing streaming data."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    statement_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.PENDING
    )
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    records: Mapped[list["StreamingRecord"]] = relationship(
        "StreamingRecord",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_job_statement_id", "statement_id", unique=True),
        Index("idx_job_file_hash", "file_hash"),
        Index("idx_job_status", "status"),
        Index("idx_job_statement_date", "statement_date"),
    )

    def __repr__(self) -> str:
        return f"IngestionJob({self.statement_id}, {self.status.value})"


class StreamingRecord(Base):
    """Individual streaming record from a statement."""

    __tablename__ = "streaming_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id"), nullable=False
    )
    track_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    track_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    streams: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped["IngestionJob"] = relationship("IngestionJob", back_populates="records")

    __table_args__ = (
        Index("idx_record_job", "job_id"),
        Index("idx_record_track", "track_id"),
        Index("idx_record_statement_date", "statement_date"),
    )

    def __repr__(self) -> str:
        return f"StreamingRecord({self.track_id}, {self.streams} streams)"