"""Ledger service - double-entry accounting logic."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.exceptions import AccountNotFoundError, LedgerBalanceError
from src.common.money import Money
from src.ledger.models import (
    STANDARD_ACCOUNTS,
    Account,
    AccountType,
    JournalEntry,
    JournalStatus,
    LedgerPosting,
    NormalBalance,
    get_normal_balance,
)


@dataclass
class PostingLine:
    account_id: UUID
    amount: Money
    is_debit: bool
    memo: str | None = None


class LedgerService:
    """Double-entry accounting ledger. Ensures debits = credits."""

    def __init__(self, db: Session):
        self.db = db

    # Account operations

    def get_account(self, account_id: UUID) -> Account:
        account = self.db.get(Account, account_id)
        if not account:
            raise AccountNotFoundError(account_id=str(account_id))
        return account

    def get_account_by_number(self, account_number: str) -> Account:
        stmt = select(Account).where(Account.account_number == account_number)
        account = self.db.execute(stmt).scalar_one_or_none()
        if not account:
            raise AccountNotFoundError(account_number=account_number)
        return account

    def list_accounts(self, account_type: AccountType | None = None) -> list[Account]:
        stmt = select(Account).order_by(Account.account_number)
        if account_type:
            stmt = stmt.where(Account.account_type == account_type)
        return list(self.db.execute(stmt).scalars().all())

    def create_account(
        self,
        account_number: str,
        name: str,
        account_type: AccountType,
        party_id: UUID | None = None,
        is_system_account: bool = False,
        description: str | None = None,
    ) -> Account:
        account = Account(
            account_number=account_number,
            name=name,
            account_type=account_type,
            normal_balance=get_normal_balance(account_type),
            party_id=party_id,
            is_system_account=is_system_account,
            description=description,
        )
        self.db.add(account)
        self.db.flush()
        return account

    def get_account_balance(self, account_id: UUID) -> Money:
        """Calculate current balance for an account."""
        account = self.get_account(account_id)

        stmt = (
            select(LedgerPosting)
            .join(JournalEntry)
            .where(
                LedgerPosting.account_id == account_id,
                JournalEntry.status.in_([JournalStatus.POSTED, JournalStatus.REVERSED]),
            )
        )
        postings = self.db.execute(stmt).scalars().all()

        total_debits = sum(p.amount_micros for p in postings if p.is_debit)
        total_credits = sum(p.amount_micros for p in postings if not p.is_debit)

        if account.normal_balance == NormalBalance.DEBIT:
            balance = total_debits - total_credits
        else:
            balance = total_credits - total_debits

        return Money(micros=balance)

    # Journal entry operations

    def create_journal_entry(
        self,
        occurred_at: datetime,
        description: str,
        postings: list[PostingLine],
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        auto_post: bool = True,
    ) -> JournalEntry:
        """Create a balanced journal entry."""
        if len(postings) < 2:
            raise ValueError("Journal entry requires at least 2 postings")

        # Balance validation
        total_debits = sum(p.amount.micros for p in postings if p.is_debit)
        total_credits = sum(p.amount.micros for p in postings if not p.is_debit)

        if total_debits != total_credits:
            raise LedgerBalanceError(
                f"Entry does not balance: debits={total_debits}, credits={total_credits}",
                debits=total_debits,
                credits=total_credits,
            )

        # Validate accounts exist
        for posting in postings:
            self.get_account(posting.account_id)

        journal = JournalEntry(
            occurred_at=occurred_at,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            status=JournalStatus.PENDING,
        )
        self.db.add(journal)
        self.db.flush()

        for seq, posting in enumerate(postings, start=1):
            ledger_posting = LedgerPosting(
                journal_entry_id=journal.id,
                account_id=posting.account_id,
                amount_micros=posting.amount.micros,
                is_debit=posting.is_debit,
                memo=posting.memo,
                sequence_number=seq,
            )
            self.db.add(ledger_posting)

        self.db.flush()

        if auto_post:
            self._post_journal_entry(journal)

        return journal

    def _post_journal_entry(self, journal: JournalEntry) -> None:
        if journal.status == JournalStatus.POSTED:
            raise ValueError("Journal entry already posted")
        journal.status = JournalStatus.POSTED
        journal.posted_at = datetime.now(timezone.utc)
        self.db.flush()

    def get_journal_entry(self, entry_id: UUID) -> JournalEntry | None:
        return self.db.get(JournalEntry, entry_id)

    def list_journal_entries(
        self,
        status: JournalStatus | None = None,
        reference_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[JournalEntry], int]:
        stmt = select(JournalEntry).order_by(JournalEntry.occurred_at.desc())

        if status:
            stmt = stmt.where(JournalEntry.status == status)
        if reference_type:
            stmt = stmt.where(JournalEntry.reference_type == reference_type)

        count_stmt = select(JournalEntry)
        if status:
            count_stmt = count_stmt.where(JournalEntry.status == status)
        if reference_type:
            count_stmt = count_stmt.where(JournalEntry.reference_type == reference_type)
        total = len(list(self.db.execute(count_stmt).scalars().all()))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        entries = list(self.db.execute(stmt).scalars().all())

        return entries, total

    def reverse_journal_entry(
        self,
        entry_id: UUID,
        occurred_at: datetime | None = None,
        description: str | None = None,
    ) -> JournalEntry:
        """Create a reversal entry with opposite postings."""
        original = self.get_journal_entry(entry_id)
        if not original:
            raise ValueError(f"Journal entry {entry_id} not found")

        if original.status == JournalStatus.REVERSED:
            raise ValueError("Journal entry already reversed")

        if original.status != JournalStatus.POSTED:
            raise ValueError("Can only reverse posted entries")

        reversed_postings = [
            PostingLine(
                account_id=p.account_id,
                amount=Money(micros=p.amount_micros),
                is_debit=not p.is_debit,
                memo=f"Reversal: {p.memo}" if p.memo else "Reversal",
            )
            for p in original.postings
        ]

        reversal = self.create_journal_entry(
            occurred_at=occurred_at or datetime.now(timezone.utc),
            description=description or f"Reversal of: {original.description}",
            postings=reversed_postings,
            reference_type="reversal",
            reference_id=original.id,
        )

        original.status = JournalStatus.REVERSED
        self.db.flush()

        return reversal

    # Reporting

    def get_trial_balance(self, as_of_date: datetime | None = None) -> dict:
        """Generate trial balance report."""
        accounts = self.list_accounts()
        line_items = []
        total_debits = 0
        total_credits = 0

        for account in accounts:
            balance = self.get_account_balance(account.id)

            if account.normal_balance == NormalBalance.DEBIT:
                if balance.micros >= 0:
                    debit_balance = balance.micros
                    credit_balance = 0
                else:
                    debit_balance = 0
                    credit_balance = abs(balance.micros)
            else:
                if balance.micros >= 0:
                    debit_balance = 0
                    credit_balance = balance.micros
                else:
                    debit_balance = abs(balance.micros)
                    credit_balance = 0

            total_debits += debit_balance
            total_credits += credit_balance

            line_items.append({
                "account_number": account.account_number,
                "account_name": account.name,
                "account_type": account.account_type,
                "debit_balance_micros": debit_balance,
                "credit_balance_micros": credit_balance,
            })

        return {
            "as_of_date": as_of_date or datetime.now(timezone.utc),
            "line_items": line_items,
            "total_debits_micros": total_debits,
            "total_credits_micros": total_credits,
            "is_balanced": total_debits == total_credits,
        }

    # Seeding

    def seed_standard_accounts(self) -> list[Account]:
        """Create standard chart of accounts."""
        created = []
        for acct in STANDARD_ACCOUNTS:
            try:
                self.get_account_by_number(acct["number"])
                continue
            except AccountNotFoundError:
                pass

            account = self.create_account(
                account_number=acct["number"],
                name=acct["name"],
                account_type=acct["type"],
                is_system_account=acct.get("system", False),
            )
            created.append(account)

        self.db.commit()
        return created
