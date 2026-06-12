"""RBAC dependencies for FastAPI routes (FOMO-149).

Role hierarchy (human roles):
    admin > manager > moderator > user

service is a standalone machine role — admin cannot substitute for service
credentials and service cannot substitute for any human role.

Usage:
    @router.get("/admin-only")
    async def admin_endpoint(user: Annotated[User, Depends(require_admin)]) -> ...:
        ...

All dependencies return the internal FOMO User model.
401 is raised for unauthenticated requests; 403 for insufficient role.
"""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.security.dependencies import require_authenticated_identity
from app.db.session import get_db
from app.schemas.identity import TokenIdentity
from app.services.user_identity_service import UserIdentityService
from packages.domain.models.user import User, UserSystemRole

_MANAGER_AND_ABOVE = frozenset({UserSystemRole.admin, UserSystemRole.manager})
_MODERATOR_AND_ABOVE = frozenset(
    {UserSystemRole.admin, UserSystemRole.manager, UserSystemRole.moderator}
)


def require_authenticated_user(
    identity: Annotated[TokenIdentity, Depends(require_authenticated_identity)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """Return the internal FOMO User for any authenticated caller.

    Creates the user on first access via UserIdentityService (idempotent).
    Delegates 401 to require_authenticated_identity when no valid token is present.
    system_role is never overwritten here — it is only set by admin tooling.
    """
    service = UserIdentityService(session)
    user, _ = service.get_or_create_from_identity(identity)
    return user


def require_admin(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require admin system role. Raises 403 for any other role."""
    if user.system_role != UserSystemRole.admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


def require_manager(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require manager or above (admin, manager). Raises 403 otherwise."""
    if user.system_role not in _MANAGER_AND_ABOVE:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


def require_moderator(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require moderator or above (admin, manager, moderator). Raises 403 otherwise."""
    if user.system_role not in _MODERATOR_AND_ABOVE:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


def require_service(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require service role.

    Service is a standalone machine role — human roles (including admin) do not
    satisfy this check.  Use separate service account credentials.
    Raises 403 for any non-service role.
    """
    if user.system_role != UserSystemRole.service:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user
