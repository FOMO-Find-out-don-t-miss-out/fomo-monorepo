import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlmodel import Session, text
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/health")
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
