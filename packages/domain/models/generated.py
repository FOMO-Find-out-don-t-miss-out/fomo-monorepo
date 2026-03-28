from datetime import datetime

from pydantic import BaseModel


class GeneratedEvent(BaseModel):
    id: str
    title: str
    description: str
    timestamp: datetime
    lat: float
    lng: float
