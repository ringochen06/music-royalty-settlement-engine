"""Contract models - revenue split agreements."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
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


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class Contract(Base):
    """Revenue split contract for a track/asset."""

    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    track_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"), default=ContractStatus.DRAFT
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    splits: Mapped[list["ContractSplit"]] = relationship(
        "ContractSplit",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractSplit.share_bps.desc()",
    )

    __table_args__ = (
        Index("idx_contract_status", "status"),
        Index("idx_contract_track", "track_id"),
        Index("idx_contract_dates", "effective_date", "expiry_date"),
    )

    def __repr__(self) -> str:
        return f"Contract({self.name}, track={self.track_id}, {self.status.value})"


class ContractSplit(Base):
    """Individual party share within a contract."""

    __tablename__ = "contract_splits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False
    )
    share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    contract: Mapped["Contract"] = relationship("Contract", back_populates="splits")
    party: Mapped["src.parties.models.Party"] = relationship(
        "Party", back_populates="contract_splits"
    )

    __table_args__ = (
        CheckConstraint("share_bps > 0", name="positive_share"),
        CheckConstraint("share_bps <= 10000", name="max_share"),
        Index("idx_split_contract", "contract_id"),
        Index("idx_split_party", "party_id"),
    )

    def __repr__(self) -> str:
        return f"ContractSplit(party={self.party_id}, {self.share_bps} BPS)"
