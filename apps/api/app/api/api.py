from fastapi import APIRouter

from app.api.v1 import health, internal, moderation

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(internal.router, prefix="/internal", tags=["internal"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
