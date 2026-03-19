from sqlmodel import create_engine, SQLModel, Session
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/fomo"

    class Config:
        env_file = ".env"


settings = Settings()

# SQLModel Engine (built on SQLAlchemy)
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
