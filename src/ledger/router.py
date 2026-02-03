"""Ledger API routes."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.common.exceptions import AccountNotFoundError, LedgerBalanceError
from src.common.money import Money
from src.database import get_db
from src.ledger.models import AccountType, JournalStatus
from src.ledger.schemas import (
    AccountBalanceResponse,
    AccountCreate,
    AccountResponse,
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryResponse,
    PostingLineResponse,
    TrialBalanceLineItem,
    TrialBalanceResponse,
)
from src.ledger.service import LedgerService, PostingLine

router = APIRouter()


def get_ledger_service(db: Session = Depends(get_db)) -> LedgerService:
    return LedgerService(db)


# Accounts

@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    account_type: AccountType | None = None,
    service: LedgerService = Depends(get_ledger_service),
) -> list[AccountResponse]:
    accounts = service.list_accounts(account_type=account_type)
    return [AccountResponse.model_validate(a) for a in accounts]


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate,
    service: LedgerService = Depends(get_ledger_service),
    db: Session = Depends(get_db),
) -> AccountResponse:
    account = service.create_account(
        account_number=data.account_number,
        name=data.name,
        account_type=data.account_type,
        party_id=data.party_id,
        is_system_account=data.is_system_account,
        description=data.description,
    )
    db.commit()
    return AccountResponse.model_validate(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    service: LedgerService = Depends(get_ledger_service),
) -> AccountResponse:
    try:
        account = service.get_account(account_id)
        return AccountResponse.model_validate(account)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/accounts/{account_id}/balance", response_model=AccountBalanceResponse)
def get_account_balance(
    account_id: UUID,
    service: LedgerService = Depends(get_ledger_service),
) -> AccountBalanceResponse:
    try:
        account = service.get_account(account_id)
        balance = service.get_account_balance(account_id)
        return AccountBalanceResponse(
            account_id=account.id,
            account_number=account.account_number,
            account_name=account.name,
            balance_micros=balance.micros,
            balance_dollars=balance.to_dollars(),
            normal_balance=account.normal_balance,
        )
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/accounts/seed", response_model=list[AccountResponse])
def seed_accounts(
    service: LedgerService = Depends(get_ledger_service),
) -> list[AccountResponse]:
    accounts = service.seed_standard_accounts()
    return [AccountResponse.model_validate(a) for a in accounts]


# Journal entries

@router.get("/journal-entries", response_model=JournalEntryListResponse)
def list_journal_entries(
    status: JournalStatus | None = None,
    reference_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    service: LedgerService = Depends(get_ledger_service),
) -> JournalEntryListResponse:
    entries, total = service.list_journal_entries(
        status=status, reference_type=reference_type, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size

    return JournalEntryListResponse(
        items=[_entry_to_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    data: JournalEntryCreate,
    service: LedgerService = Depends(get_ledger_service),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    try:
        postings = [
            PostingLine(
                account_id=p.account_id,
                amount=Money(micros=p.amount_micros),
                is_debit=p.is_debit,
                memo=p.memo,
            )
            for p in data.postings
        ]

        entry = service.create_journal_entry(
            occurred_at=data.occurred_at,
            description=data.description,
            postings=postings,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
        )
        db.commit()
        return _entry_to_response(entry)
    except LedgerBalanceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(
    entry_id: UUID,
    service: LedgerService = Depends(get_ledger_service),
) -> JournalEntryResponse:
    entry = service.get_journal_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return _entry_to_response(entry)


@router.post("/journal-entries/{entry_id}/reverse", response_model=JournalEntryResponse, status_code=201)
def reverse_journal_entry(
    entry_id: UUID,
    service: LedgerService = Depends(get_ledger_service),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    try:
        reversal = service.reverse_journal_entry(entry_id)
        db.commit()
        return _entry_to_response(reversal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Trial balance

@router.get("/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    service: LedgerService = Depends(get_ledger_service),
) -> TrialBalanceResponse:
    data = service.get_trial_balance()
    return TrialBalanceResponse(
        as_of_date=data["as_of_date"],
        line_items=[
            TrialBalanceLineItem(
                account_number=item["account_number"],
                account_name=item["account_name"],
                account_type=item["account_type"],
                debit_balance_micros=item["debit_balance_micros"],
                credit_balance_micros=item["credit_balance_micros"],
            )
            for item in data["line_items"]
        ],
        total_debits_micros=data["total_debits_micros"],
        total_credits_micros=data["total_credits_micros"],
        is_balanced=data["is_balanced"],
    )


# Helper

def _entry_to_response(entry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        occurred_at=entry.occurred_at,
        created_at=entry.created_at,
        description=entry.description,
        reference_type=entry.reference_type,
        reference_id=entry.reference_id,
        status=entry.status,
        posted_at=entry.posted_at,
        postings=[
            PostingLineResponse(
                id=p.id,
                account_id=p.account_id,
                amount_micros=p.amount_micros,
                is_debit=p.is_debit,
                memo=p.memo,
                sequence_number=p.sequence_number,
            )
            for p in entry.postings
        ],
    )
