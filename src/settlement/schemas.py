"""Pydantic schemas for the settlements API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.settlement.models import SettlementStatus


class SettlementRunCreate(BaseModel):
    job_id: UUID


# Allocation (party-level share within a line)


class SettlementAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_id: UUID
    party_id: UUID
    share_bps: int
    amount_micros: int


# Settlement line (per-track detail)


class SettlementLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    track_id: str
    track_name: str
    contract_id: UUID | None
    gross_micros: int
    platform_fee_micros: int
    net_micros: int
    is_unmatched: bool
    journal_entry_id: UUID | None
    created_at: datetime
    allocations: list[SettlementAllocationResponse] = []


class SettlementLineListResponse(BaseModel):
    items: list[SettlementLineResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Settlement run


class SettlementRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    statement_id: str
    status: SettlementStatus
    platform_fee_bps: int

    total_tracks: int
    matched_tracks: int
    unmatched_tracks: int

    total_gross_micros: int
    total_platform_fee_micros: int
    total_net_micros: int
    total_unmatched_micros: int

    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    lines: list[SettlementLineResponse] = []


class SettlementRunListResponse(BaseModel):
    items: list[SettlementRunResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
