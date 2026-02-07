"""Pydantic schemas for parties API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.parties.models import PartyStatus, PartyType


class PartyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    party_type: PartyType
    email: str | None = None
    phone: str | None = None
    external_id: str | None = None
    notes: str | None = None


class PartyCreate(PartyBase):
    pass


class PartyUpdate(BaseModel):
    """Partial update - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    status: PartyStatus | None = None
    notes: str | None = None


class PartyResponse(PartyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: PartyStatus
    created_at: datetime
    updated_at: datetime


class PartyListResponse(BaseModel):
    items: list[PartyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
