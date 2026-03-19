from typing import Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from geoalchemy2 import Geography


class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    start_time: datetime
    end_time: datetime
    hype_score: int = Field(default=0, index=True)
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
