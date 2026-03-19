from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/fomo"
    REDIS_URL: str = "redis://redis:6379/0"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FOMO API"
    N8N_WEBHOOK_URL: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
