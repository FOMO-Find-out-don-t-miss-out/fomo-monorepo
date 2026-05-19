from app.repositories.place_repository import PlaceRepository
from sqlmodel import Session

from packages.domain.models import PlaceVerificationStatus


def test_save_new_place(session: Session):
    repo = PlaceRepository(session)
    place = repo.save_place(
        name="Test Place",
        country_code="GR",
        lat=37.9838,
        lng=23.7275,
        full_address="Athens, Greece",
        relevance=1.0,
        city="Athens",
    )

    assert place.id is not None
    assert place.name == "Test Place"
    assert place.city == "Athens"


def test_get_by_name_exact(session: Session):
    repo = PlaceRepository(session)
    repo.save_place("Unique Place", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    found = repo.get_by_name("Unique Place", "GR")
    assert found is not None
    assert found.name == "Unique Place"


def test_get_by_name_fuzzy(session: Session):
    repo = PlaceRepository(session)
    repo.save_place("The Great Club", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    found = repo.get_by_name("The Great Clu", "GR")
    assert found is not None
    assert found.name == "The Great Club"


def test_get_by_name_city_mismatch(session: Session):
    repo = PlaceRepository(session)
    repo.save_place("Common Name", "GR", 1.0, 1.0, "Addr", 1.0, "Athens")

    found = repo.get_by_name("Common Name", "GR", city_hint="Thessaloniki")
    assert found is None


def test_update_not_verified(session: Session):
    repo = PlaceRepository(session)
    repo.save_place("Place", "GR", 1.0, 1.0, "Old Addr", 0.5)

    updated = repo.save_place("Place", "GR", 2.0, 2.0, "New Addr", 1.0)
    assert updated.lat == 2.0
    assert updated.full_address == "New Addr"


def test_do_not_update_manually_verified(session: Session):
    repo = PlaceRepository(session)
    p = repo.save_place("Verified Place", "GR", 1.0, 1.0, "Original", 1.0)
    p.verification_status = PlaceVerificationStatus.manually_verified
    session.add(p)
    session.commit()

    updated = repo.save_place("Verified Place", "GR", 9.0, 9.0, "Hack", 0.1)
    assert updated.lat == 1.0
    assert updated.full_address == "Original"


def test_delete_places(session: Session):
    repo = PlaceRepository(session)
    repo.save_place("P1", "GR", 1.0, 1.0, "A1", 1.0)
    repo.save_place("P2", "GR", 2.0, 2.0, "A2", 1.0)

    count = repo.delete_places("P1")
    assert count == 1
    assert repo.get_by_name("P1", "GR") is None
    assert repo.get_by_name("P2", "GR") is not None

    count = repo.delete_places()
    assert count == 1
    assert repo.get_by_name("P2", "GR") is None


def test_venue_repository_alias_works(session: Session):
    """VenueRepository is a backward-compat alias for PlaceRepository."""
    from app.repositories.venue_repository import VenueRepository

    assert VenueRepository is PlaceRepository
    repo = VenueRepository(session)
    p = repo.save_venue("Alias Place", "GR", 1.0, 1.0, "A", 1.0)
    assert p.name == "Alias Place"
    count = repo.delete_venues("Alias Place")
    assert count == 1
