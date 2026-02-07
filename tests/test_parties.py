"""Tests for the parties module."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.exceptions import PartyNotFoundError
from src.database import Base
from src.ledger.models import AccountType
from src.parties.models import PartyStatus, PartyType
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


class TestPartyCreation:

    def test_create_artist(self, party_service, db_session):
        party = party_service.create_party(
            name="Taylor Swift",
            party_type=PartyType.ARTIST,
            email="taylor@example.com",
        )
        db_session.commit()

        assert party.name == "Taylor Swift"
        assert party.party_type == PartyType.ARTIST
        assert party.status == PartyStatus.ACTIVE
        assert party.email == "taylor@example.com"

    def test_create_label(self, party_service, db_session):
        party = party_service.create_party(
            name="Universal Music",
            party_type=PartyType.LABEL,
        )
        db_session.commit()

        assert party.party_type == PartyType.LABEL

    def test_create_party_auto_creates_account(self, party_service, db_session):
        party = party_service.create_party(
            name="Test Artist",
            party_type=PartyType.ARTIST,
        )
        db_session.commit()

        # Query for the auto-created account
        from src.ledger.models import Account
        from sqlalchemy import select

        stmt = select(Account).where(Account.party_id == party.id)
        account = db_session.execute(stmt).scalar_one_or_none()

        assert account is not None
        assert account.account_type == AccountType.LIABILITY
        assert account.name == "Test Artist Payable"
        assert account.account_number.startswith("2100-")

    def test_create_producer_account_prefix(self, party_service, db_session):
        party = party_service.create_party(
            name="Max Martin",
            party_type=PartyType.PRODUCER,
        )
        db_session.commit()

        from src.ledger.models import Account
        from sqlalchemy import select

        stmt = select(Account).where(Account.party_id == party.id)
        account = db_session.execute(stmt).scalar_one_or_none()

        assert account.account_number.startswith("2300-")

    def test_create_party_with_external_id(self, party_service, db_session):
        party = party_service.create_party(
            name="External Artist",
            party_type=PartyType.ARTIST,
            external_id="EXT-001",
        )
        db_session.commit()

        assert party.external_id == "EXT-001"


class TestPartyRetrieval:

    def test_get_party(self, party_service, db_session):
        party = party_service.create_party(
            name="Test",
            party_type=PartyType.ARTIST,
        )
        db_session.commit()

        found = party_service.get_party(party.id)
        assert found.name == "Test"

    def test_get_nonexistent_party_raises(self, party_service):
        with pytest.raises(PartyNotFoundError):
            party_service.get_party(uuid4())


class TestPartyUpdate:

    def test_update_name(self, party_service, db_session):
        party = party_service.create_party(
            name="Old Name",
            party_type=PartyType.ARTIST,
        )
        db_session.commit()

        updated = party_service.update_party(party.id, name="New Name")
        db_session.commit()

        assert updated.name == "New Name"

    def test_update_status(self, party_service, db_session):
        party = party_service.create_party(
            name="Test",
            party_type=PartyType.ARTIST,
        )
        db_session.commit()

        updated = party_service.update_party(party.id, status=PartyStatus.INACTIVE)
        db_session.commit()

        assert updated.status == PartyStatus.INACTIVE

    def test_partial_update(self, party_service, db_session):
        party = party_service.create_party(
            name="Test",
            party_type=PartyType.ARTIST,
            email="old@example.com",
        )
        db_session.commit()

        updated = party_service.update_party(party.id, email="new@example.com")
        db_session.commit()

        assert updated.email == "new@example.com"
        assert updated.name == "Test"  # unchanged


class TestPartyListing:

    def test_list_all(self, party_service, db_session):
        party_service.create_party(name="A", party_type=PartyType.ARTIST)
        party_service.create_party(name="B", party_type=PartyType.LABEL)
        db_session.commit()

        parties, total = party_service.list_parties()
        assert total == 2

    def test_filter_by_type(self, party_service, db_session):
        party_service.create_party(name="Artist", party_type=PartyType.ARTIST)
        party_service.create_party(name="Label", party_type=PartyType.LABEL)
        db_session.commit()

        parties, total = party_service.list_parties(party_type=PartyType.ARTIST)
        assert total == 1
        assert parties[0].name == "Artist"

    def test_filter_by_status(self, party_service, db_session):
        p1 = party_service.create_party(name="Active", party_type=PartyType.ARTIST)
        p2 = party_service.create_party(name="Inactive", party_type=PartyType.ARTIST)
        party_service.update_party(p2.id, status=PartyStatus.INACTIVE)
        db_session.commit()

        parties, total = party_service.list_parties(status=PartyStatus.ACTIVE)
        assert total == 1
        assert parties[0].name == "Active"

    def test_search_by_name(self, party_service, db_session):
        party_service.create_party(name="Taylor Swift", party_type=PartyType.ARTIST)
        party_service.create_party(name="Drake", party_type=PartyType.ARTIST)
        db_session.commit()

        parties, total = party_service.list_parties(name_search="taylor")
        assert total == 1
        assert parties[0].name == "Taylor Swift"

    def test_pagination(self, party_service, db_session):
        for i in range(5):
            party_service.create_party(name=f"Party {i}", party_type=PartyType.ARTIST)
        db_session.commit()

        parties, total = party_service.list_parties(page=1, page_size=2)
        assert total == 5
        assert len(parties) == 2
