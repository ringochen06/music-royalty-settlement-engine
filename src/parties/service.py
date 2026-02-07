"""Party service - CRUD operations for music industry participants."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.common.exceptions import PartyNotFoundError
from src.ledger.models import Account, AccountType, get_normal_balance
from src.parties.models import Party, PartyStatus, PartyType


class PartyService:
    """Manages music industry participants and their ledger accounts."""

    def __init__(self, db: Session):
        self.db = db

    def get_party(self, party_id: UUID) -> Party:
        party = self.db.get(Party, party_id)
        if not party:
            raise PartyNotFoundError(party_id=str(party_id))
        return party

    def list_parties(
        self,
        party_type: PartyType | None = None,
        status: PartyStatus | None = None,
        name_search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Party], int]:
        stmt = select(Party).order_by(Party.name)

        if party_type:
            stmt = stmt.where(Party.party_type == party_type)
        if status:
            stmt = stmt.where(Party.status == status)
        if name_search:
            stmt = stmt.where(Party.name.ilike(f"%{name_search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        parties = list(self.db.execute(stmt).scalars().all())

        return parties, total

    def create_party(
        self,
        name: str,
        party_type: PartyType,
        email: str | None = None,
        phone: str | None = None,
        external_id: str | None = None,
        notes: str | None = None,
    ) -> Party:
        party = Party(
            name=name,
            party_type=party_type,
            email=email,
            phone=phone,
            external_id=external_id,
            notes=notes,
        )
        self.db.add(party)
        self.db.flush()

        # Auto-create a payable account for this party
        self._create_party_account(party)

        return party

    def update_party(
        self,
        party_id: UUID,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        status: PartyStatus | None = None,
        notes: str | None = None,
    ) -> Party:
        party = self.get_party(party_id)

        if name is not None:
            party.name = name
        if email is not None:
            party.email = email
        if phone is not None:
            party.phone = phone
        if status is not None:
            party.status = status
        if notes is not None:
            party.notes = notes

        self.db.flush()
        return party

    def _create_party_account(self, party: Party) -> Account:
        """Auto-create a LIABILITY (payable) account for the party."""
        account_prefix = self._get_account_prefix(party.party_type)
        short_id = party.id.hex[:8]
        account_number = f"{account_prefix}-{short_id}"

        account = Account(
            account_number=account_number,
            name=f"{party.name} Payable",
            account_type=AccountType.LIABILITY,
            normal_balance=get_normal_balance(AccountType.LIABILITY),
            party_id=party.id,
            is_system_account=False,
            description=f"Payable account for {party.party_type.value}: {party.name}",
        )
        self.db.add(account)
        self.db.flush()
        return account

    @staticmethod
    def _get_account_prefix(party_type: PartyType) -> str:
        """Map party type to ledger account number prefix."""
        prefixes = {
            PartyType.ARTIST: "2100",
            PartyType.LABEL: "2200",
            PartyType.PRODUCER: "2300",
            PartyType.PUBLISHER: "2400",
            PartyType.DISTRIBUTOR: "2500",
            PartyType.SONGWRITER: "2600",
        }
        return prefixes.get(party_type, "2900")
