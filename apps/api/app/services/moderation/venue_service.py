# Backward-compatibility shim — use app.services.moderation.place_service for new code.
from app.services.moderation.place_service import PlaceModerationService

VenueModerationService = PlaceModerationService

__all__ = ["PlaceModerationService", "VenueModerationService"]
