from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

# SQLModel Engine
engine = create_engine(settings.DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a session per request."""
    with Session(engine) as session:
        yield session
