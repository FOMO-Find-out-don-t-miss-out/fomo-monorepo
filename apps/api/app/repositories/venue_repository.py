# Backward-compatibility shim — use app.repositories.place_repository for new code.
from app.repositories.place_repository import PlaceRepository
from sqlmodel import Session  # re-exported so existing patches targeting this module don't break

VenueRepository = PlaceRepository

__all__ = ["PlaceRepository", "Session", "VenueRepository"]
