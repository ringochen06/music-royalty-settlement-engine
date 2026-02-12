"""Pydantic schemas for ingestion API."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.ingestion.models import JobStatus


# StreamingRecord schemas


class StreamingRecordBase(BaseModel):
    track_id: str = Field(..., min_length=1, max_length=100)
    track_name: str = Field(..., min_length=1, max_length=255)
    artist_name: str = Field(..., min_length=1, max_length=255)
    streams: int = Field(..., gt=0)
    revenue_micros: int = Field(..., gt=0)


class StreamingRecordResponse(StreamingRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    statement_date: date
    created_at: datetime

    @property
    def revenue_dollars(self) -> Decimal:
        return Decimal(self.revenue_micros) / Decimal(1_000_000)


# IngestionJob schemas


class IngestionJobCreate(BaseModel):
    statement_id: str = Field(..., min_length=1, max_length=100)
    file_name: str = Field(..., min_length=1, max_length=255)
    statement_date: date
    file_content: str = Field(..., description="CSV content as string")


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    statement_id: str
    file_hash: str
    file_name: str
    statement_date: date
    status: JobStatus
    total_records: int
    total_revenue_micros: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @property
    def total_revenue_dollars(self) -> Decimal:
        return Decimal(self.total_revenue_micros) / Decimal(1_000_000)


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StreamingRecordListResponse(BaseModel):
    items: list[StreamingRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int