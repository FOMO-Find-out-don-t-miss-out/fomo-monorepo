from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security.dependencies import require_authenticated_identity
from app.db.session import get_db
from app.schemas.identity import TokenIdentity
from app.schemas.user import UserMeResponse
from app.services.user_identity_service import UserIdentityService

router = APIRouter()


@router.get("/me", response_model=UserMeResponse)
async def get_my_user(
    identity: Annotated[TokenIdentity, Depends(require_authenticated_identity)],
    session: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    """Return the internal FOMO user and profile for the authenticated caller.

    Creates the user and a default profile on first access.
    Idempotent: repeated calls with the same Keycloak subject return
    the same record without creating duplicates.
    """
    service = UserIdentityService(session)
    user, profile = service.get_or_create_from_identity(identity)
    return UserMeResponse.from_models(user, profile)
