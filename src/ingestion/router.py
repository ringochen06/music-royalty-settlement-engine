"""Ingestion API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.common.exceptions import DuplicateIngestionError, IngestionValidationError
from src.database import get_db
from src.ingestion.models import JobStatus
from src.ingestion.schemas import (
    IngestionJobCreate,
    IngestionJobListResponse,
    IngestionJobResponse,
    StreamingRecordListResponse,
    StreamingRecordResponse,
)
from src.ingestion.service import IngestionService

router = APIRouter()


def get_ingestion_service(db: Session = Depends(get_db)) -> IngestionService:
    return IngestionService(db)


@router.get("/jobs", response_model=IngestionJobListResponse)
def list_jobs(
    status: JobStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionJobListResponse:
    jobs, total = service.list_jobs(status=status, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size
    return IngestionJobListResponse(
        items=[IngestionJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/jobs", response_model=IngestionJobResponse, status_code=201)
def create_job(
    data: IngestionJobCreate,
    service: IngestionService = Depends(get_ingestion_service),
    db: Session = Depends(get_db),
) -> IngestionJobResponse:
    try:
        job = service.create_job(
            statement_id=data.statement_id,
            file_name=data.file_name,
            statement_date=data.statement_date,
            file_content=data.file_content,
        )
        db.commit()
        return IngestionJobResponse.model_validate(job)
    except DuplicateIngestionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IngestionValidationError as e:
        raise HTTPException(status_code=400, detail={"message": str(e), "errors": e.errors})


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_job(
    job_id: UUID,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionJobResponse:
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return IngestionJobResponse.model_validate(job)


@router.get("/records", response_model=StreamingRecordListResponse)
def list_records(
    job_id: UUID | None = None,
    track_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: IngestionService = Depends(get_ingestion_service),
) -> StreamingRecordListResponse:
    records, total = service.list_records(
        job_id=job_id,
        track_id=track_id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return StreamingRecordListResponse(
        items=[StreamingRecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )