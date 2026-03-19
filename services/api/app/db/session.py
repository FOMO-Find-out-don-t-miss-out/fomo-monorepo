from sqlmodel import create_engine, Session
from app.core.config import settings

# SQLModel Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)


def get_db():
    """Dependency for providing a session per request."""
    with Session(engine) as session:
        yield session
