import redis.asyncio as redis
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic_settings import BaseSettings
from database import get_db


class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


app = FastAPI(title="FOMO API")
settings = Settings()

# Async Redis Connection Pool
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to monitor database and Redis connectivity."""
    health_status = {"status": "ok", "components": {}}

    # Postgres Connection Check
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = f"unhealthy: {str(e)}"

    # Redis Connection Check
    try:
        await redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"

    return health_status
