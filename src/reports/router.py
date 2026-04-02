"""Reports API routes - read-only financial reports."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.exceptions import SettlementRunNotFoundError
from src.database import get_db
from src.ledger.schemas import TrialBalanceResponse
from src.reports.schemas import (
    AccountBalancesReport,
    PartyStatementReport,
    SettlementSummaryReport,
)
from src.reports.service import ReportsService

router = APIRouter()


def get_reports_service(db: Session = Depends(get_db)) -> ReportsService:
    return ReportsService(db)


@router.get("/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    service: ReportsService = Depends(get_reports_service),
) -> TrialBalanceResponse:
    result = service.get_trial_balance()
    return TrialBalanceResponse(**result)


@router.get("/account-balances", response_model=AccountBalancesReport)
def get_account_balances(
    service: ReportsService = Depends(get_reports_service),
) -> AccountBalancesReport:
    return service.get_account_balances()


@router.get("/settlement-summary/{run_id}", response_model=SettlementSummaryReport)
def get_settlement_summary(
    run_id: UUID,
    service: ReportsService = Depends(get_reports_service),
) -> SettlementSummaryReport:
    try:
        return service.get_settlement_summary(run_id)
    except SettlementRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/party-statement/{party_id}", response_model=PartyStatementReport)
def get_party_statement(
    party_id: UUID,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    service: ReportsService = Depends(get_reports_service),
) -> PartyStatementReport:
    try:
        return service.get_party_statement(
            party_id=party_id, from_date=from_date, to_date=to_date
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
