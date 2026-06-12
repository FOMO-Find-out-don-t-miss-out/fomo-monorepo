from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security.dependencies import require_authenticated_identity
from app.core.security.rbac import (
    require_admin,
    require_manager,
    require_moderator,
    require_service,
)
from app.schemas.identity import TokenIdentity
from packages.domain.models.user import User

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


# ---------------------------------------------------------------------------
# RBAC canary endpoints — used by tests and dashboard feature detection
# ---------------------------------------------------------------------------


@router.get("/admin-check")
async def admin_check(user: Annotated[User, Depends(require_admin)]) -> dict:
    """Return 200 if caller has admin role, 403 otherwise."""
    return {"system_role": user.system_role}


@router.get("/manager-check")
async def manager_check(user: Annotated[User, Depends(require_manager)]) -> dict:
    """Return 200 if caller has manager or above, 403 otherwise."""
    return {"system_role": user.system_role}


@router.get("/moderator-check")
async def moderator_check(user: Annotated[User, Depends(require_moderator)]) -> dict:
    """Return 200 if caller has moderator or above, 403 otherwise."""
    return {"system_role": user.system_role}


@router.get("/service-check")
async def service_check(user: Annotated[User, Depends(require_service)]) -> dict:
    """Return 200 if caller has service role, 403 otherwise."""
    return {"system_role": user.system_role}
