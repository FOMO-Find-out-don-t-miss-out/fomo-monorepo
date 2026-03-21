from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON, UniqueConstraint
from geoalchemy2 import Geography


class EventBase(SQLModel):
    title: str
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    end_time: Optional[datetime] = None
    hype_score: int = Field(default=0, index=True)
    category: str = Field(default="Other", index=True)
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = Field(default=None, index=True)
    country_code: Optional[str] = Field(default=None, index=True)
    parent_id: Optional[UUID] = Field(default=None, index=True)


class Event(EventBase, table=True):
    __tablename__ = "events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Redefine columns using sa_column in child classes to avoid Column sharing errors
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        UniqueConstraint("title", "start_time", name="unique_event_occurrence"),
    )


class PendingEvent(EventBase, table=True):
    __tablename__ = "pending_events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Redefine columns using sa_column in child classes to avoid Column sharing errors
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    status: str = Field(default="pending", index=True)
    raw_content: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    confidence_score: Optional[float] = Field(default=None)
    geocoding_status: str = Field(default="failed", index=True)
    geocoding_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        UniqueConstraint("title", "start_time", name="unique_pending_event"),
    )
