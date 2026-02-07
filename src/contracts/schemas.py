"""Pydantic schemas for contracts API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.contracts.models import ContractStatus


# ContractSplit schemas


class ContractSplitBase(BaseModel):
    party_id: UUID
    share_bps: int = Field(..., gt=0, le=10000)
    role: str | None = None


class ContractSplitCreate(ContractSplitBase):
    pass


class ContractSplitResponse(ContractSplitBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    created_at: datetime

    @property
    def share_percentage(self) -> float:
        return self.share_bps / 100.0


# Contract schemas


class ContractBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    track_id: str = Field(..., min_length=1, max_length=100)
    effective_date: date
    expiry_date: date | None = None
    description: str | None = None


class ContractCreate(ContractBase):
    splits: list[ContractSplitCreate] = Field(..., min_length=1)

    @field_validator("splits")
    @classmethod
    def validate_splits_total(cls, v: list[ContractSplitCreate]) -> list[ContractSplitCreate]:
        total_bps = sum(s.share_bps for s in v)
        if total_bps != 10000:
            raise ValueError(
                f"Splits must total 10000 BPS (100%), got {total_bps}"
            )
        # Check for duplicate parties
        party_ids = [s.party_id for s in v]
        if len(party_ids) != len(set(party_ids)):
            raise ValueError("Duplicate party_id in splits")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "ContractCreate":
        if self.expiry_date and self.expiry_date <= self.effective_date:
            raise ValueError("expiry_date must be after effective_date")
        return self


class ContractUpdate(BaseModel):
    """Partial update - status transitions and metadata."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: ContractStatus | None = None
    expiry_date: date | None = None
    description: str | None = None


class ContractResponse(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ContractStatus
    created_at: datetime
    updated_at: datetime
    splits: list[ContractSplitResponse] = []


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
