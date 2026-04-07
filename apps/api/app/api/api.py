from fastapi import APIRouter

from app.api.v1 import events, health, ingestion, moderation

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
