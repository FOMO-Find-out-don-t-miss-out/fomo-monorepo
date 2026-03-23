from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON, UniqueConstraint
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from pydantic import field_serializer, computed_field


class EventBase(SQLModel):
    title: str
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    end_time: Optional[datetime] = None
    hype_score: int = Field(default=0, index=True)
    category: str = Field(default="Other", index=True)
    sub_category: Optional[str] = Field(default=None, index=True)
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = Field(default=None, index=True)
    country_code: Optional[str] = Field(default=None, index=True)
    parent_id: Optional[UUID] = Field(default=None, index=True)

    @computed_field
    @property
    def photo_url(self) -> Optional[str]:
        """Returns the photo URL from metadata, normalized to be absolute."""
        if not self.event_metadata:
            return None
        
        url = self.event_metadata.get("photo_url") or self.event_metadata.get("image")
        if not url:
            return None
        
        if isinstance(url, list):
            url = url[0] if url else None
            
        if not isinstance(url, str):
            return None
            
        url = url.strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("www."):
            return f"https://{url}"
        
        # If it's a relative path and we have a source_url, we could try to join them
        # but for now we just return as is if it doesn't match above patterns
        return url


class Event(EventBase, table=True):
    __tablename__ = "events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Redefine columns using sa_column in child classes to avoid Column sharing errors
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    __table_args__ = (
        UniqueConstraint("title", "start_time", name="unique_event_occurrence"),
    )

    @field_serializer("location")
    def serialize_location(self, v: Any):
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v


class PendingEvent(EventBase, table=True):
    __tablename__ = "pending_events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Redefine columns using sa_column in child classes to avoid Column sharing errors
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    status: str = Field(default="pending", index=True)
    raw_content: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    confidence_score: Optional[float] = Field(default=None)
    geocoding_status: str = Field(default="failed", index=True)
    geocoding_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        UniqueConstraint("title", "start_time", name="unique_pending_event"),
    )

    @field_serializer("location")
    def serialize_location(self, v: Any):
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v
