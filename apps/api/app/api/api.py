from fastapi import APIRouter

from app.api.v1 import admin, events, health, identity, ingestion, me, moderation, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
