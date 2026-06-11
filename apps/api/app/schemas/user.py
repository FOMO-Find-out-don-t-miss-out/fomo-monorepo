from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from packages.domain.models.user import Profile, User


class UserMeResponse(BaseModel):
    """Response schema for GET /api/v1/users/me.

    Exposes internal user/profile state for the authenticated caller.
    Wallet balance and transactions are intentionally excluded (separate domain).
    Phone fields are present but only populated by the OTP flow (FOMO-149+).
    """

    id: UUID
    external_id: str
    email: str | None
    phone_number: str | None
    phone_verified: bool
    username: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_models(cls, user: User, profile: Profile) -> "UserMeResponse":
        return cls(
            id=user.id,
            external_id=user.external_id,
            email=user.email,
            phone_number=user.phone_number,
            phone_verified=user.phone_verified,
            username=profile.username,
            avatar_url=profile.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
