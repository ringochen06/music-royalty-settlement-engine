"""Tests for the ledger module."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.exceptions import AccountNotFoundError, LedgerBalanceError
from src.common.money import Money
from src.database import Base
from src.ledger.models import AccountType, JournalStatus, NormalBalance
from src.ledger.service import LedgerService, PostingLine


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def ledger_service(db_session) -> LedgerService:
    return LedgerService(db_session)


@pytest.fixture
def accounts(ledger_service):
    ledger_service.seed_standard_accounts()
    return {a.account_number: a for a in ledger_service.list_accounts()}


class TestAccounts:

    def test_create_account(self, ledger_service, db_session):
        asset = ledger_service.create_account("1001", "Cash", AccountType.ASSET)
        liability = ledger_service.create_account("2001", "Payable", AccountType.LIABILITY)
        db_session.commit()

        assert asset.normal_balance == NormalBalance.DEBIT
        assert liability.normal_balance == NormalBalance.CREDIT

    def test_get_account_by_number(self, ledger_service, db_session):
        ledger_service.create_account("1002", "Test", AccountType.ASSET)
        db_session.commit()
        assert ledger_service.get_account_by_number("1002").name == "Test"

    def test_nonexistent_account_raises(self, ledger_service):
        with pytest.raises(AccountNotFoundError):
            ledger_service.get_account(uuid4())

    def test_seed_standard_accounts(self, ledger_service):
        accounts = ledger_service.seed_standard_accounts()
        numbers = [a.account_number for a in accounts]
        assert "1000" in numbers
        assert "4000" in numbers


class TestJournalEntries:

    def test_create_balanced_entry(self, accounts, ledger_service, db_session):
        cash = accounts["1000"]
        revenue = accounts["4100"]

        entry = ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Revenue receipt",
            postings=[
                PostingLine(cash.id, Money.from_dollars("100"), is_debit=True),
                PostingLine(revenue.id, Money.from_dollars("100"), is_debit=False),
            ],
        )
        db_session.commit()

        assert entry.status == JournalStatus.POSTED
        assert len(entry.postings) == 2

    def test_unbalanced_entry_rejected(self, accounts, ledger_service):
        cash = accounts["1000"]
        revenue = accounts["4100"]

        with pytest.raises(LedgerBalanceError) as exc:
            ledger_service.create_journal_entry(
                occurred_at=datetime.utcnow(),
                description="Unbalanced",
                postings=[
                    PostingLine(cash.id, Money.from_dollars("100"), is_debit=True),
                    PostingLine(revenue.id, Money.from_dollars("50"), is_debit=False),
                ],
            )
        assert exc.value.debits == 100_000_000
        assert exc.value.credits == 50_000_000

    def test_single_posting_rejected(self, accounts, ledger_service):
        with pytest.raises(ValueError, match="at least 2 postings"):
            ledger_service.create_journal_entry(
                occurred_at=datetime.utcnow(),
                description="Single",
                postings=[PostingLine(accounts["1000"].id, Money.from_dollars("100"), is_debit=True)],
            )

    def test_invalid_account_rejected(self, accounts, ledger_service):
        with pytest.raises(AccountNotFoundError):
            ledger_service.create_journal_entry(
                occurred_at=datetime.utcnow(),
                description="Invalid",
                postings=[
                    PostingLine(accounts["1000"].id, Money.from_dollars("100"), is_debit=True),
                    PostingLine(uuid4(), Money.from_dollars("100"), is_debit=False),
                ],
            )


class TestBalanceCalculation:

    def test_debit_increases_asset(self, accounts, ledger_service, db_session):
        cash = accounts["1000"]
        revenue = accounts["4100"]

        ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Revenue",
            postings=[
                PostingLine(cash.id, Money.from_dollars("1000"), is_debit=True),
                PostingLine(revenue.id, Money.from_dollars("1000"), is_debit=False),
            ],
        )
        db_session.commit()

        assert ledger_service.get_account_balance(cash.id).to_dollars() == Decimal("1000")

    def test_credit_increases_liability(self, accounts, ledger_service, db_session):
        cash = accounts["1000"]
        payable = accounts["2100"]

        ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Payable",
            postings=[
                PostingLine(cash.id, Money.from_dollars("500"), is_debit=True),
                PostingLine(payable.id, Money.from_dollars("500"), is_debit=False),
            ],
        )
        db_session.commit()

        assert ledger_service.get_account_balance(payable.id).to_dollars() == Decimal("500")


class TestReversals:

    def test_reverse_entry(self, accounts, ledger_service, db_session):
        cash = accounts["1000"]
        revenue = accounts["4100"]

        original = ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Original",
            postings=[
                PostingLine(cash.id, Money.from_dollars("100"), is_debit=True),
                PostingLine(revenue.id, Money.from_dollars("100"), is_debit=False),
            ],
        )
        db_session.commit()

        reversal = ledger_service.reverse_journal_entry(original.id)
        db_session.commit()
        db_session.refresh(original)

        assert original.status == JournalStatus.REVERSED
        assert reversal.reference_type == "reversal"
        assert ledger_service.get_account_balance(cash.id).micros == 0

    def test_cannot_double_reverse(self, accounts, ledger_service, db_session):
        cash = accounts["1000"]
        revenue = accounts["4100"]

        original = ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Original",
            postings=[
                PostingLine(cash.id, Money.from_dollars("100"), is_debit=True),
                PostingLine(revenue.id, Money.from_dollars("100"), is_debit=False),
            ],
        )
        db_session.commit()

        ledger_service.reverse_journal_entry(original.id)
        db_session.commit()

        with pytest.raises(ValueError, match="already reversed"):
            ledger_service.reverse_journal_entry(original.id)


class TestTrialBalance:

    def test_trial_balance(self, accounts, ledger_service, db_session):
        tb = ledger_service.get_trial_balance()
        assert tb["is_balanced"] is True

        ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Entry",
            postings=[
                PostingLine(accounts["1000"].id, Money.from_dollars("1000"), is_debit=True),
                PostingLine(accounts["4100"].id, Money.from_dollars("1000"), is_debit=False),
            ],
        )
        db_session.commit()

        tb = ledger_service.get_trial_balance()
        assert tb["is_balanced"] is True
        assert tb["total_debits_micros"] == tb["total_credits_micros"]


class TestMultiLineEntry:

    def test_revenue_split_entry(self, accounts, ledger_service, db_session):
        entry = ledger_service.create_journal_entry(
            occurred_at=datetime.utcnow(),
            description="Revenue split",
            postings=[
                PostingLine(accounts["1000"].id, Money.from_dollars("100"), is_debit=True),
                PostingLine(accounts["4000"].id, Money.from_dollars("15"), is_debit=False),
                PostingLine(accounts["2100"].id, Money.from_dollars("50"), is_debit=False),
                PostingLine(accounts["2200"].id, Money.from_dollars("35"), is_debit=False),
            ],
        )
        db_session.commit()

        assert len(entry.postings) == 4
        assert ledger_service.get_account_balance(accounts["2100"].id).to_dollars() == Decimal("50")
        assert ledger_service.get_trial_balance()["is_balanced"] is True
