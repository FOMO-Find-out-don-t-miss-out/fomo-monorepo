from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from packages.domain.models.event_relationship import RelationshipType


class RelationshipResponse(BaseModel):
    id: UUID
    event_id: UUID
    relationship_type: RelationshipType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventRelationshipsResponse(BaseModel):
    relationships: dict[str, list[RelationshipType]]
