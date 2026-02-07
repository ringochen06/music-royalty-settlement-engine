"""Tests for the contracts module."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.exceptions import ContractNotFoundError, InvalidSplitError, PartyNotFoundError
from src.contracts.models import ContractStatus
from src.contracts.service import ContractService
from src.database import Base
from src.parties.models import PartyType
from src.parties.service import PartyService


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def party_service(db_session) -> PartyService:
    return PartyService(db_session)


@pytest.fixture
def contract_service(db_session) -> ContractService:
    return ContractService(db_session)


@pytest.fixture
def parties(party_service, db_session):
    """Create test parties for contract testing."""
    artist = party_service.create_party(name="Artist", party_type=PartyType.ARTIST)
    label = party_service.create_party(name="Label", party_type=PartyType.LABEL)
    producer = party_service.create_party(name="Producer", party_type=PartyType.PRODUCER)
    db_session.commit()
    return {"artist": artist, "label": label, "producer": producer}


class TestContractCreation:

    def test_create_contract_with_valid_splits(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Song A Deal",
            track_id="TRACK-001",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000, "role": "lead artist"},
                {"party_id": parties["label"].id, "share_bps": 3500, "role": "label"},
                {"party_id": parties["producer"].id, "share_bps": 1500, "role": "producer"},
            ],
        )
        db_session.commit()

        assert contract.name == "Song A Deal"
        assert contract.track_id == "TRACK-001"
        assert contract.status == ContractStatus.DRAFT
        assert len(contract.splits) == 3
        assert sum(s.share_bps for s in contract.splits) == 10000

    def test_create_contract_two_way_split(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Simple Deal",
            track_id="TRACK-002",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 6000},
                {"party_id": parties["label"].id, "share_bps": 4000},
            ],
        )
        db_session.commit()

        assert len(contract.splits) == 2

    def test_invalid_splits_not_100_percent(self, parties, contract_service):
        with pytest.raises(InvalidSplitError):
            contract_service.create_contract(
                name="Bad Deal",
                track_id="TRACK-003",
                effective_date=date(2026, 1, 1),
                splits=[
                    {"party_id": parties["artist"].id, "share_bps": 5000},
                    {"party_id": parties["label"].id, "share_bps": 3000},
                ],
            )

    def test_invalid_party_id(self, parties, contract_service):
        with pytest.raises(PartyNotFoundError):
            contract_service.create_contract(
                name="Bad Deal",
                track_id="TRACK-004",
                effective_date=date(2026, 1, 1),
                splits=[
                    {"party_id": parties["artist"].id, "share_bps": 5000},
                    {"party_id": uuid4(), "share_bps": 5000},
                ],
            )

    def test_create_with_expiry_date(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Limited Deal",
            track_id="TRACK-005",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 12, 31),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()

        assert contract.expiry_date == date(2027, 12, 31)


class TestContractRetrieval:

    def test_get_contract(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Test",
            track_id="TRACK-010",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()

        found = contract_service.get_contract(contract.id)
        assert found.name == "Test"
        assert len(found.splits) == 2

    def test_get_nonexistent_contract_raises(self, contract_service):
        with pytest.raises(ContractNotFoundError):
            contract_service.get_contract(uuid4())


class TestContractStatusTransitions:

    def _create_draft_contract(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Test",
            track_id="TRACK-020",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()
        return contract

    def test_draft_to_active(self, parties, contract_service, db_session):
        contract = self._create_draft_contract(parties, contract_service, db_session)

        activated = contract_service.activate_contract(contract.id)
        db_session.commit()

        assert activated.status == ContractStatus.ACTIVE

    def test_active_to_terminated(self, parties, contract_service, db_session):
        contract = self._create_draft_contract(parties, contract_service, db_session)
        contract_service.activate_contract(contract.id)
        db_session.commit()

        terminated = contract_service.terminate_contract(contract.id)
        db_session.commit()

        assert terminated.status == ContractStatus.TERMINATED

    def test_draft_to_terminated(self, parties, contract_service, db_session):
        contract = self._create_draft_contract(parties, contract_service, db_session)

        terminated = contract_service.terminate_contract(contract.id)
        db_session.commit()

        assert terminated.status == ContractStatus.TERMINATED

    def test_invalid_transition_terminated_to_active(self, parties, contract_service, db_session):
        contract = self._create_draft_contract(parties, contract_service, db_session)
        contract_service.terminate_contract(contract.id)
        db_session.commit()

        with pytest.raises(ValueError, match="Invalid status transition"):
            contract_service.activate_contract(contract.id)

    def test_invalid_transition_expired_to_active(self, parties, contract_service, db_session):
        contract = self._create_draft_contract(parties, contract_service, db_session)
        contract_service.activate_contract(contract.id)
        contract_service.update_contract(contract.id, status=ContractStatus.EXPIRED)
        db_session.commit()

        with pytest.raises(ValueError, match="Invalid status transition"):
            contract_service.activate_contract(contract.id)


class TestContractUpdate:

    def test_update_name(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Old Name",
            track_id="TRACK-030",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()

        updated = contract_service.update_contract(contract.id, name="New Name")
        db_session.commit()

        assert updated.name == "New Name"

    def test_update_description(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Test",
            track_id="TRACK-031",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()

        updated = contract_service.update_contract(contract.id, description="Updated desc")
        db_session.commit()

        assert updated.description == "Updated desc"


class TestContractListing:

    def test_list_all(self, parties, contract_service, db_session):
        for i in range(3):
            contract_service.create_contract(
                name=f"Contract {i}",
                track_id=f"TRACK-{i}",
                effective_date=date(2026, 1, 1),
                splits=[
                    {"party_id": parties["artist"].id, "share_bps": 5000},
                    {"party_id": parties["label"].id, "share_bps": 5000},
                ],
            )
        db_session.commit()

        contracts, total = contract_service.list_contracts()
        assert total == 3

    def test_filter_by_status(self, parties, contract_service, db_session):
        c1 = contract_service.create_contract(
            name="Draft",
            track_id="TRACK-A",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        c2 = contract_service.create_contract(
            name="Active",
            track_id="TRACK-B",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        contract_service.activate_contract(c2.id)
        db_session.commit()

        contracts, total = contract_service.list_contracts(status=ContractStatus.ACTIVE)
        assert total == 1
        assert contracts[0].name == "Active"

    def test_filter_by_track(self, parties, contract_service, db_session):
        contract_service.create_contract(
            name="C1",
            track_id="TRACK-X",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        contract_service.create_contract(
            name="C2",
            track_id="TRACK-Y",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        db_session.commit()

        contracts, total = contract_service.list_contracts(track_id="TRACK-X")
        assert total == 1
        assert contracts[0].name == "C1"

    def test_get_active_contract_for_track(self, parties, contract_service, db_session):
        contract = contract_service.create_contract(
            name="Active Deal",
            track_id="TRACK-FIND",
            effective_date=date(2026, 1, 1),
            splits=[
                {"party_id": parties["artist"].id, "share_bps": 5000},
                {"party_id": parties["label"].id, "share_bps": 5000},
            ],
        )
        contract_service.activate_contract(contract.id)
        db_session.commit()

        found = contract_service.get_active_contract_for_track("TRACK-FIND")
        assert found is not None
        assert found.name == "Active Deal"

    def test_no_active_contract_for_track(self, contract_service):
        found = contract_service.get_active_contract_for_track("NONEXISTENT")
        assert found is None

    def test_pagination(self, parties, contract_service, db_session):
        for i in range(5):
            contract_service.create_contract(
                name=f"Contract {i}",
                track_id=f"TRACK-P{i}",
                effective_date=date(2026, 1, 1),
                splits=[
                    {"party_id": parties["artist"].id, "share_bps": 5000},
                    {"party_id": parties["label"].id, "share_bps": 5000},
                ],
            )
        db_session.commit()

        contracts, total = contract_service.list_contracts(page=1, page_size=2)
        assert total == 5
        assert len(contracts) == 2
