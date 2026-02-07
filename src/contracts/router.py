"""Contracts API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.common.exceptions import ContractNotFoundError, InvalidSplitError, PartyNotFoundError
from src.contracts.models import ContractStatus
from src.contracts.schemas import (
    ContractCreate,
    ContractListResponse,
    ContractResponse,
    ContractSplitResponse,
    ContractUpdate,
)
from src.contracts.service import ContractService
from src.database import get_db

router = APIRouter()


def get_contract_service(db: Session = Depends(get_db)) -> ContractService:
    return ContractService(db)


@router.get("/", response_model=ContractListResponse)
def list_contracts(
    status: ContractStatus | None = None,
    track_id: str | None = None,
    party_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: ContractService = Depends(get_contract_service),
) -> ContractListResponse:
    contracts, total = service.list_contracts(
        status=status,
        track_id=track_id,
        party_id=party_id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return ContractListResponse(
        items=[_contract_to_response(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/", response_model=ContractResponse, status_code=201)
def create_contract(
    data: ContractCreate,
    service: ContractService = Depends(get_contract_service),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        contract = service.create_contract(
            name=data.name,
            track_id=data.track_id,
            effective_date=data.effective_date,
            splits=[
                {
                    "party_id": s.party_id,
                    "share_bps": s.share_bps,
                    "role": s.role,
                }
                for s in data.splits
            ],
            expiry_date=data.expiry_date,
            description=data.description,
        )
        db.commit()
        return _contract_to_response(contract)
    except InvalidSplitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PartyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: UUID,
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    try:
        contract = service.get_contract(contract_id)
        return _contract_to_response(contract)
    except ContractNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: UUID,
    data: ContractUpdate,
    service: ContractService = Depends(get_contract_service),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        contract = service.update_contract(
            contract_id=contract_id,
            name=data.name,
            status=data.status,
            expiry_date=data.expiry_date,
            description=data.description,
        )
        db.commit()
        return _contract_to_response(contract)
    except ContractNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/activate", response_model=ContractResponse)
def activate_contract(
    contract_id: UUID,
    service: ContractService = Depends(get_contract_service),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        contract = service.activate_contract(contract_id)
        db.commit()
        return _contract_to_response(contract)
    except ContractNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/terminate", response_model=ContractResponse)
def terminate_contract(
    contract_id: UUID,
    service: ContractService = Depends(get_contract_service),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        contract = service.terminate_contract(contract_id)
        db.commit()
        return _contract_to_response(contract)
    except ContractNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _contract_to_response(contract: "Contract") -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        name=contract.name,
        track_id=contract.track_id,
        status=contract.status,
        effective_date=contract.effective_date,
        expiry_date=contract.expiry_date,
        description=contract.description,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
        splits=[
            ContractSplitResponse(
                id=s.id,
                contract_id=s.contract_id,
                party_id=s.party_id,
                share_bps=s.share_bps,
                role=s.role,
                created_at=s.created_at,
            )
            for s in contract.splits
        ],
    )
