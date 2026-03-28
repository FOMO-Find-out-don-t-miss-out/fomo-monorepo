from typing import Annotated, Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/health")
async def health_check(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    """Health check endpoint to monitor database and Redis connectivity."""
    health_status: dict[str, Any] = {"status": "ok", "components": {}}

    # Postgres Connection Check
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = f"unhealthy: {e!s}"

    # Redis Connection Check
    try:
        await redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["redis"] = f"unhealthy: {e!s}"

    return health_status
