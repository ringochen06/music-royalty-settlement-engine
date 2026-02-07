"""Contract service - revenue split agreement management."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.common.exceptions import (
    ContractNotFoundError,
    InvalidSplitError,
    PartyNotFoundError,
)
from src.common.money import BasisPoints, validate_splits_total
from src.contracts.models import Contract, ContractSplit, ContractStatus
from src.parties.models import Party


class ContractService:
    """Manages revenue split contracts between parties."""

    def __init__(self, db: Session):
        self.db = db

    def get_contract(self, contract_id: UUID) -> Contract:
        contract = self.db.get(Contract, contract_id)
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        return contract

    def list_contracts(
        self,
        status: ContractStatus | None = None,
        track_id: str | None = None,
        party_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Contract], int]:
        stmt = select(Contract).order_by(Contract.created_at.desc())

        if status:
            stmt = stmt.where(Contract.status == status)
        if track_id:
            stmt = stmt.where(Contract.track_id == track_id)
        if party_id:
            stmt = stmt.where(
                Contract.splits.any(ContractSplit.party_id == party_id)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        contracts = list(self.db.execute(stmt).scalars().all())

        return contracts, total

    def create_contract(
        self,
        name: str,
        track_id: str,
        effective_date: date,
        splits: list[dict],
        expiry_date: date | None = None,
        description: str | None = None,
    ) -> Contract:
        """Create a contract with splits.

        splits: list of {"party_id": UUID, "share_bps": int, "role": str | None}
        """
        # Validate splits total to 10000 BPS
        bps_list = [BasisPoints(value=s["share_bps"]) for s in splits]
        if not validate_splits_total(bps_list):
            total = sum(s["share_bps"] for s in splits)
            raise InvalidSplitError(
                message=f"Splits must total 10000 BPS (100%), got {total}",
                total_bps=total,
            )

        # Validate all parties exist
        for split in splits:
            party = self.db.get(Party, split["party_id"])
            if not party:
                raise PartyNotFoundError(party_id=str(split["party_id"]))

        contract = Contract(
            name=name,
            track_id=track_id,
            effective_date=effective_date,
            expiry_date=expiry_date,
            description=description,
            status=ContractStatus.DRAFT,
        )
        self.db.add(contract)
        self.db.flush()

        for split_data in splits:
            split = ContractSplit(
                contract_id=contract.id,
                party_id=split_data["party_id"],
                share_bps=split_data["share_bps"],
                role=split_data.get("role"),
            )
            self.db.add(split)

        self.db.flush()
        return contract

    def update_contract(
        self,
        contract_id: UUID,
        name: str | None = None,
        status: ContractStatus | None = None,
        expiry_date: date | None = None,
        description: str | None = None,
    ) -> Contract:
        contract = self.get_contract(contract_id)

        if status is not None:
            self._validate_status_transition(contract.status, status)
            contract.status = status
        if name is not None:
            contract.name = name
        if expiry_date is not None:
            contract.expiry_date = expiry_date
        if description is not None:
            contract.description = description

        self.db.flush()
        return contract

    def activate_contract(self, contract_id: UUID) -> Contract:
        """Transition contract from DRAFT to ACTIVE."""
        return self.update_contract(contract_id, status=ContractStatus.ACTIVE)

    def terminate_contract(self, contract_id: UUID) -> Contract:
        """Terminate an active contract."""
        return self.update_contract(contract_id, status=ContractStatus.TERMINATED)

    def get_active_contract_for_track(self, track_id: str) -> Contract | None:
        """Find the active contract for a given track. Used by settlement engine."""
        stmt = (
            select(Contract)
            .where(
                Contract.track_id == track_id,
                Contract.status == ContractStatus.ACTIVE,
            )
            .order_by(Contract.effective_date.desc())
        )
        return self.db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _validate_status_transition(
        current: ContractStatus, target: ContractStatus
    ) -> None:
        """Enforce valid contract status transitions."""
        valid_transitions = {
            ContractStatus.DRAFT: {ContractStatus.ACTIVE, ContractStatus.TERMINATED},
            ContractStatus.ACTIVE: {ContractStatus.EXPIRED, ContractStatus.TERMINATED},
            ContractStatus.EXPIRED: set(),
            ContractStatus.TERMINATED: set(),
        }
        allowed = valid_transitions.get(current, set())
        if target not in allowed:
            raise ValueError(
                f"Invalid status transition: {current.value} -> {target.value}"
            )
