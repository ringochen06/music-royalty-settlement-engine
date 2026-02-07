"""Party models - music industry participants."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database import Base


class PartyType(str, enum.Enum):
    ARTIST = "artist"
    LABEL = "label"
    PRODUCER = "producer"
    PUBLISHER = "publisher"
    DISTRIBUTOR = "distributor"
    SONGWRITER = "songwriter"


class PartyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Party(Base):
    """A music industry participant (artist, label, producer, etc.)."""

    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    party_type: Mapped[PartyType] = mapped_column(
        Enum(PartyType, name="party_type"), nullable=False
    )
    status: Mapped[PartyStatus] = mapped_column(
        Enum(PartyStatus, name="party_status"), default=PartyStatus.ACTIVE
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship to ledger accounts owned by this party
    accounts: Mapped[list["src.ledger.models.Account"]] = relationship(
        "Account",
        primaryjoin="Party.id == Account.party_id",
        foreign_keys="Account.party_id",
        viewonly=True,
    )

    # Relationship to contract splits this party participates in
    contract_splits: Mapped[list["src.contracts.models.ContractSplit"]] = relationship(
        "ContractSplit", back_populates="party"
    )

    __table_args__ = (
        Index("idx_party_type", "party_type"),
        Index("idx_party_status", "status"),
        Index("idx_party_name", "name"),
    )

    def __repr__(self) -> str:
        return f"Party({self.name}, {self.party_type.value})"
