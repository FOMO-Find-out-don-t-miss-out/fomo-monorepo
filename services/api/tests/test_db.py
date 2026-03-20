import pytest
from app.db.session import get_db, engine
from sqlmodel import Session

def test_get_db_yields_session():
    """Test get_db dependency."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    assert session.bind == engine
    # Cleanup
    try:
        next(db_gen)
    except StopIteration:
        pass
