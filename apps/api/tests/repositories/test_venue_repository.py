from app.repositories.venue_repository import VenueRepository
from sqlmodel import Session


def test_save_new_venue(session: Session):
    repo = VenueRepository(session)
    venue = repo.save_venue(
        name="Test Venue",
        country_code="GR",
        lat=37.9838,
        lng=23.7275,
        full_address="Athens, Greece",
        relevance=1.0,
        city="Athens",
    )

    assert venue.id is not None
    assert venue.name == "Test Venue"
    assert venue.city == "Athens"


def test_get_by_name_exact(session: Session):
    repo = VenueRepository(session)
    repo.save_venue("Unique Venue", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    found = repo.get_by_name("Unique Venue", "GR")
    assert found is not None
    assert found.name == "Unique Venue"


def test_get_by_name_fuzzy(session: Session):
    repo = VenueRepository(session)
    repo.save_venue("The Great Club", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    # 0.9+ similarity
    found = repo.get_by_name("The Great Clu", "GR")
    assert found is not None
    assert found.name == "The Great Club"


def test_get_by_name_city_mismatch(session: Session):
    repo = VenueRepository(session)
    repo.save_venue("Common Name", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    # Same name, different city hint
    found = repo.get_by_name("Common Name", "GR", city_hint="Thessaloniki")
    assert found is None


def test_update_not_verified(session: Session):
    repo = VenueRepository(session)
    repo.save_venue("Venue", "GR", 1.0, 1.0, "Old Addr", 0.5)

    updated = repo.save_venue("Venue", "GR", 2.0, 2.0, "New Addr", 1.0)
    assert updated.lat == 2.0
    assert updated.full_address == "New Addr"


def test_do_not_update_manually_verified(session: Session):
    repo = VenueRepository(session)
    v = repo.save_venue("Verified Venue", "GR", 1.0, 1.0, "Original", 1.0)
    v.is_manually_verified = True
    session.add(v)
    session.commit()

    updated = repo.save_venue("Verified Venue", "GR", 9.0, 9.0, "Hack", 0.1)
    assert updated.lat == 1.0
    assert updated.full_address == "Original"


def test_delete_venues(session: Session):
    repo = VenueRepository(session)
    repo.save_venue("V1", "GR", 1.0, 1.0, "A1", 1.0)
    repo.save_venue("V2", "GR", 2.0, 2.0, "A2", 1.0)

    count = repo.delete_venues("V1")
    assert count == 1
    assert repo.get_by_name("V1", "GR") is None
    assert repo.get_by_name("V2", "GR") is not None

    count = repo.delete_venues()
    assert count == 1
    assert repo.get_by_name("V2", "GR") is None
