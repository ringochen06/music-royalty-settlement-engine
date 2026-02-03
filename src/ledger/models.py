"""Double-entry accounting models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"
    EXPENSE = "expense"


class NormalBalance(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class JournalStatus(str, enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    REVERSED = "reversed"


class Account(Base):
    """Chart of accounts entry."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type"), nullable=False
    )
    normal_balance: Mapped[NormalBalance] = mapped_column(
        Enum(NormalBalance, name="normal_balance"), nullable=False
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_system_account: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    postings: Mapped[list["LedgerPosting"]] = relationship(
        "LedgerPosting", back_populates="account"
    )

    def __repr__(self) -> str:
        return f"Account({self.account_number}: {self.name})"


class JournalEntry(Base):
    """Header for a set of balanced postings."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[JournalStatus] = mapped_column(
        Enum(JournalStatus, name="journal_status"), default=JournalStatus.PENDING
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    postings: Mapped[list["LedgerPosting"]] = relationship(
        "LedgerPosting",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="LedgerPosting.sequence_number",
    )

    __table_args__ = (
        Index("idx_journal_status", "status"),
        Index("idx_journal_occurred_at", "occurred_at"),
        Index("idx_journal_reference", "reference_type", "reference_id"),
    )

    def __repr__(self) -> str:
        return f"JournalEntry({self.id}, {self.status.value}: {self.description[:30]})"


class LedgerPosting(Base):
    """Individual debit or credit line."""

    __tablename__ = "ledger_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    amount_micros: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_debit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    journal_entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry", back_populates="postings"
    )
    account: Mapped["Account"] = relationship("Account", back_populates="postings")

    __table_args__ = (
        CheckConstraint("amount_micros > 0", name="positive_amount"),
        Index("idx_postings_journal", "journal_entry_id"),
        Index("idx_postings_account", "account_id"),
    )

    def __repr__(self) -> str:
        side = "DR" if self.is_debit else "CR"
        return f"LedgerPosting({side} {self.amount_micros} micros)"


# Standard chart of accounts
STANDARD_ACCOUNTS = [
    {"number": "1000", "name": "Cash", "type": AccountType.ASSET, "system": True},
    {"number": "1100", "name": "Accounts Receivable", "type": AccountType.ASSET, "system": True},
    {"number": "2000", "name": "Revenue Clearing", "type": AccountType.LIABILITY, "system": True},
    {"number": "2100", "name": "Artist Payables", "type": AccountType.LIABILITY, "system": True},
    {"number": "2200", "name": "Label Payables", "type": AccountType.LIABILITY, "system": True},
    {"number": "2300", "name": "Producer Payables", "type": AccountType.LIABILITY, "system": True},
    {"number": "4000", "name": "Platform Fee Revenue", "type": AccountType.REVENUE, "system": True},
    {"number": "4100", "name": "Streaming Revenue", "type": AccountType.REVENUE, "system": True},
    {"number": "5000", "name": "Operating Expenses", "type": AccountType.EXPENSE, "system": True},
]


def get_normal_balance(account_type: AccountType) -> NormalBalance:
    if account_type in (AccountType.ASSET, AccountType.EXPENSE):
        return NormalBalance.DEBIT
    return NormalBalance.CREDIT
