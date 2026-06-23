from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from app.core.security.rbac import require_authenticated_user
from app.db.session import get_db
from app.schemas.me import EventRelationshipsResponse, RelationshipResponse
from app.services.event_relationship_service import EventRelationshipService
from packages.domain.models.event_relationship import RelationshipType
from packages.domain.models.user import User
from packages.domain.schemas.event import EventDiscoveryResponse

router = APIRouter()


@router.put(
    "/events/{event_id}/relationships/{relationship_type}",
    response_model=RelationshipResponse,
)
async def put_relationship(
    event_id: UUID,
    relationship_type: RelationshipType,
    user: Annotated[User, Depends(require_authenticated_user)],
    session: Annotated[Session, Depends(get_db)],
) -> RelationshipResponse:
    service = EventRelationshipService(session)
    result = service.mark_relationship(
        user_id=user.id,
        event_id=event_id,
        relationship_type=relationship_type,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found or not available")
    return RelationshipResponse.model_validate(result)


@router.delete(
    "/events/{event_id}/relationships/{relationship_type}",
    status_code=204,
)
async def delete_relationship(
    event_id: UUID,
    relationship_type: RelationshipType,
    user: Annotated[User, Depends(require_authenticated_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service = EventRelationshipService(session)
    ok = service.remove_relationship(
        user_id=user.id,
        event_id=event_id,
        relationship_type=relationship_type,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or not available")
    return Response(status_code=204)


@router.get("/saved-events", response_model=list[EventDiscoveryResponse])
async def get_saved_events(
    user: Annotated[User, Depends(require_authenticated_user)],
    session: Annotated[Session, Depends(get_db)],
) -> list[EventDiscoveryResponse]:
    service = EventRelationshipService(session)
    events = service.list_saved_events(user_id=user.id)
    return [EventDiscoveryResponse.model_validate(e) for e in events]


@router.get("/event-relationships", response_model=EventRelationshipsResponse)
async def get_event_relationships(
    user: Annotated[User, Depends(require_authenticated_user)],
    session: Annotated[Session, Depends(get_db)],
    event_ids: Annotated[list[UUID] | None, Query()] = None,
) -> EventRelationshipsResponse:
    service = EventRelationshipService(session)
    mapping = service.get_relationships_for_events(user_id=user.id, event_ids=event_ids or [])
    return EventRelationshipsResponse(
        relationships={str(k): v for k, v in mapping.items()}
    )
