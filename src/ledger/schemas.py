"""Pydantic schemas for ledger API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.ledger.models import AccountType, JournalStatus, NormalBalance


# Account schemas

class AccountBase(BaseModel):
    account_number: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    account_type: AccountType
    description: str | None = None


class AccountCreate(AccountBase):
    party_id: UUID | None = None
    is_system_account: bool = False


class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    normal_balance: NormalBalance
    party_id: UUID | None
    is_system_account: bool
    created_at: datetime


class AccountBalanceResponse(BaseModel):
    account_id: UUID
    account_number: str
    account_name: str
    balance_micros: int
    balance_dollars: Decimal
    normal_balance: NormalBalance


# Posting schemas

class PostingLineCreate(BaseModel):
    account_id: UUID
    amount_micros: int = Field(..., gt=0)
    is_debit: bool
    memo: str | None = None

    @field_validator("amount_micros")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_micros must be positive")
        return v


class PostingLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    amount_micros: int
    is_debit: bool
    memo: str | None
    sequence_number: int

    @property
    def amount_dollars(self) -> Decimal:
        return Decimal(self.amount_micros) / Decimal(1_000_000)

    @property
    def side(self) -> str:
        return "debit" if self.is_debit else "credit"


# Journal entry schemas

class JournalEntryCreate(BaseModel):
    occurred_at: datetime
    description: str = Field(..., min_length=1)
    reference_type: str | None = None
    reference_id: UUID | None = None
    postings: list[PostingLineCreate] = Field(..., min_length=2)

    @field_validator("postings")
    @classmethod
    def validate_balance(cls, v: list[PostingLineCreate]) -> list[PostingLineCreate]:
        total_debits = sum(p.amount_micros for p in v if p.is_debit)
        total_credits = sum(p.amount_micros for p in v if not p.is_debit)
        if total_debits != total_credits:
            raise ValueError(f"Entry must balance: debits={total_debits}, credits={total_credits}")
        return v


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    created_at: datetime
    description: str
    reference_type: str | None
    reference_id: UUID | None
    status: JournalStatus
    posted_at: datetime | None
    postings: list[PostingLineResponse] = []

    @property
    def total_debits_micros(self) -> int:
        return sum(p.amount_micros for p in self.postings if p.is_debit)

    @property
    def total_credits_micros(self) -> int:
        return sum(p.amount_micros for p in self.postings if not p.is_debit)


class JournalEntryListResponse(BaseModel):
    items: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Trial balance schemas

class TrialBalanceLineItem(BaseModel):
    account_number: str
    account_name: str
    account_type: AccountType
    debit_balance_micros: int = 0
    credit_balance_micros: int = 0

    @property
    def debit_balance_dollars(self) -> Decimal:
        return Decimal(self.debit_balance_micros) / Decimal(1_000_000)

    @property
    def credit_balance_dollars(self) -> Decimal:
        return Decimal(self.credit_balance_micros) / Decimal(1_000_000)


class TrialBalanceResponse(BaseModel):
    as_of_date: datetime
    line_items: list[TrialBalanceLineItem]
    total_debits_micros: int
    total_credits_micros: int
    is_balanced: bool

    @property
    def total_debits_dollars(self) -> Decimal:
        return Decimal(self.total_debits_micros) / Decimal(1_000_000)

    @property
    def total_credits_dollars(self) -> Decimal:
        return Decimal(self.total_credits_micros) / Decimal(1_000_000)
