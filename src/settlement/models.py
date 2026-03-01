"""Settlement models - royalty settlement runs."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class SettlementStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SettlementRun(Base):
    """A settlement run processes one completed IngestionJob into ledger entries."""

    __tablename__ = "settlement_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Idempotency key — one run per ingestion job
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_jobs.id"),
        nullable=False,
        unique=True,
    )
    statement_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[SettlementStatus] = mapped_column(
        Enum(SettlementStatus, name="settlement_status"), default=SettlementStatus.PENDING
    )
    # Snapshot of fee rate so historical runs remain auditable
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False)

    total_tracks: Mapped[int] = mapped_column(Integer, default=0)
    matched_tracks: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_tracks: Mapped[int] = mapped_column(Integer, default=0)

    total_gross_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    total_platform_fee_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    total_net_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    total_unmatched_micros: Mapped[int] = mapped_column(BigInteger, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["SettlementLine"]] = relationship(
        "SettlementLine",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SettlementLine.track_id",
    )

    __table_args__ = (
        Index("idx_run_job_id", "job_id", unique=True),
        Index("idx_run_status", "status"),
        Index("idx_run_statement_id", "statement_id"),
    )

    def __repr__(self) -> str:
        return f"SettlementRun({self.statement_id}, {self.status.value})"


class SettlementLine(Base):
    """Per-track settlement detail within a run."""

    __tablename__ = "settlement_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("settlement_runs.id"), nullable=False
    )
    track_id: Mapped[str] = mapped_column(String(100), nullable=False)
    track_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )

    gross_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    platform_fee_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    net_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_unmatched: Mapped[bool] = mapped_column(Boolean, default=False)

    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["SettlementRun"] = relationship("SettlementRun", back_populates="lines")
    allocations: Mapped[list["SettlementAllocation"]] = relationship(
        "SettlementAllocation",
        back_populates="line",
        cascade="all, delete-orphan",
        order_by="SettlementAllocation.amount_micros.desc()",
    )

    __table_args__ = (
        Index("idx_line_run", "run_id"),
        Index("idx_line_track", "track_id"),
    )

    def __repr__(self) -> str:
        return f"SettlementLine({self.track_id}, gross={self.gross_micros})"


class SettlementAllocation(Base):
    """Party-level allocation within a settlement line."""

    __tablename__ = "settlement_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("settlement_lines.id"), nullable=False
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False
    )
    share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    line: Mapped["SettlementLine"] = relationship("SettlementLine", back_populates="allocations")

    __table_args__ = (
        Index("idx_alloc_line", "line_id"),
        Index("idx_alloc_party", "party_id"),
    )

    def __repr__(self) -> str:
        return f"SettlementAllocation(party={self.party_id}, {self.amount_micros} micros)"
