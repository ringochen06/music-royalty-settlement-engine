"""Settlements API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.common.exceptions import (
    DuplicateSettlementError,
    IngestionJobNotFoundError,
    SettlementRunNotFoundError,
)
from src.database import get_db
from src.settlement.models import SettlementStatus
from src.settlement.schemas import (
    SettlementLineListResponse,
    SettlementLineResponse,
    SettlementRunCreate,
    SettlementRunListResponse,
    SettlementRunResponse,
)
from src.settlement.service import SettlementService

router = APIRouter()


def get_settlement_service(db: Session = Depends(get_db)) -> SettlementService:
    return SettlementService(db)


@router.post("/runs", response_model=SettlementRunResponse, status_code=201)
def create_run(
    data: SettlementRunCreate,
    service: SettlementService = Depends(get_settlement_service),
    db: Session = Depends(get_db),
) -> SettlementRunResponse:
    try:
        run = service.create_run(job_id=data.job_id)
        db.commit()
        return _run_to_response(run)
    except DuplicateSettlementError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IngestionJobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs", response_model=SettlementRunListResponse)
def list_runs(
    status: SettlementStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementRunListResponse:
    runs, total = service.list_runs(status=status, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size
    return SettlementRunListResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/runs/{run_id}", response_model=SettlementRunResponse)
def get_run(
    run_id: UUID,
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementRunResponse:
    try:
        run = service.get_run(run_id)
        return _run_to_response(run)
    except SettlementRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/lines", response_model=SettlementLineListResponse)
def list_lines(
    run_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: SettlementService = Depends(get_settlement_service),
) -> SettlementLineListResponse:
    try:
        lines, total = service.list_lines(run_id=run_id, page=page, page_size=page_size)
        total_pages = (total + page_size - 1) // page_size
        return SettlementLineListResponse(
            items=[_line_to_response(ln) for ln in lines],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except SettlementRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Helpers ---


def _run_to_response(run: "SettlementRun") -> SettlementRunResponse:
    from src.settlement.models import SettlementRun  # avoid circular at module level
    from src.settlement.schemas import SettlementAllocationResponse

    return SettlementRunResponse(
        id=run.id,
        job_id=run.job_id,
        statement_id=run.statement_id,
        status=run.status,
        platform_fee_bps=run.platform_fee_bps,
        total_tracks=run.total_tracks,
        matched_tracks=run.matched_tracks,
        unmatched_tracks=run.unmatched_tracks,
        total_gross_micros=run.total_gross_micros,
        total_platform_fee_micros=run.total_platform_fee_micros,
        total_net_micros=run.total_net_micros,
        total_unmatched_micros=run.total_unmatched_micros,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        lines=[_line_to_response(ln) for ln in run.lines],
    )


def _line_to_response(line: "SettlementLine") -> SettlementLineResponse:
    from src.settlement.schemas import SettlementAllocationResponse

    return SettlementLineResponse(
        id=line.id,
        run_id=line.run_id,
        track_id=line.track_id,
        track_name=line.track_name,
        contract_id=line.contract_id,
        gross_micros=line.gross_micros,
        platform_fee_micros=line.platform_fee_micros,
        net_micros=line.net_micros,
        is_unmatched=line.is_unmatched,
        journal_entry_id=line.journal_entry_id,
        created_at=line.created_at,
        allocations=[
            SettlementAllocationResponse(
                id=a.id,
                line_id=a.line_id,
                party_id=a.party_id,
                share_bps=a.share_bps,
                amount_micros=a.amount_micros,
            )
            for a in line.allocations
        ],
    )
