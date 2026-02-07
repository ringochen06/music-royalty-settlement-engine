"""Parties API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.common.exceptions import PartyNotFoundError
from src.database import get_db
from src.parties.models import PartyStatus, PartyType
from src.parties.schemas import (
    PartyCreate,
    PartyListResponse,
    PartyResponse,
    PartyUpdate,
)
from src.parties.service import PartyService

router = APIRouter()


def get_party_service(db: Session = Depends(get_db)) -> PartyService:
    return PartyService(db)


@router.get("/", response_model=PartyListResponse)
def list_parties(
    party_type: PartyType | None = None,
    status: PartyStatus | None = None,
    name: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: PartyService = Depends(get_party_service),
) -> PartyListResponse:
    parties, total = service.list_parties(
        party_type=party_type,
        status=status,
        name_search=name,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return PartyListResponse(
        items=[PartyResponse.model_validate(p) for p in parties],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/", response_model=PartyResponse, status_code=201)
def create_party(
    data: PartyCreate,
    service: PartyService = Depends(get_party_service),
    db: Session = Depends(get_db),
) -> PartyResponse:
    party = service.create_party(
        name=data.name,
        party_type=data.party_type,
        email=data.email,
        phone=data.phone,
        external_id=data.external_id,
        notes=data.notes,
    )
    db.commit()
    return PartyResponse.model_validate(party)


@router.get("/{party_id}", response_model=PartyResponse)
def get_party(
    party_id: UUID,
    service: PartyService = Depends(get_party_service),
) -> PartyResponse:
    try:
        party = service.get_party(party_id)
        return PartyResponse.model_validate(party)
    except PartyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{party_id}", response_model=PartyResponse)
def update_party(
    party_id: UUID,
    data: PartyUpdate,
    service: PartyService = Depends(get_party_service),
    db: Session = Depends(get_db),
) -> PartyResponse:
    try:
        party = service.update_party(
            party_id=party_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            status=data.status,
            notes=data.notes,
        )
        db.commit()
        return PartyResponse.model_validate(party)
    except PartyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
