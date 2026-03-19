from fastapi import APIRouter
from app.api.v1 import health, internal

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(internal.router, prefix="/internal", tags=["internal"])
