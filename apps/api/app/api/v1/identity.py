from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security.dependencies import require_authenticated_identity
from app.schemas.identity import TokenIdentity

router = APIRouter()


@router.get("/me", response_model=TokenIdentity)
async def get_my_identity(
    identity: Annotated[TokenIdentity, Depends(require_authenticated_identity)],
) -> TokenIdentity:
    """Return the validated identity of the authenticated caller.

    Requires a valid Keycloak Bearer JWT.  Useful for verifying authentication
    from the dashboard and as a canary for OIDC configuration.
    """
    return identity
