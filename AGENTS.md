# AGENTS.md - FOMO Monorepo Agent Guidelines

## Project Overview

This is a **Python FastAPI monorepo** for a real-time event discovery platform:
- **`services/api`** - FastAPI backend (SQLModel, SQLAlchemy 2.0, Pydantic v2, PostGIS, Redis)
- **`apps/mobile`** - Expo/React Native mobile app (planned)
- **`infra/`** - Docker and database provisioning scripts

## Build/Lint/Test Commands

All commands run from `services/api/` directory or via Docker Compose.

### Running the API
```bash
# Start infrastructure
docker compose up -d --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Linting (Ruff)
```bash
# Lint entire project
docker compose exec api ruff check .

# Auto-fix linting issues
docker compose exec api ruff check --fix .

# Lint specific file
docker compose exec api ruff check app/models/event.py
```

### Testing (Pytest)
```bash
# Run all tests
docker compose exec api pytest

# Run with coverage report
docker compose exec api pytest --cov=app --cov-report=term-missing

# Run a single test file
docker compose exec api pytest tests/test_cleanser.py

# Run a single test
docker compose exec api pytest tests/test_cleanser.py::test_clean_json_ld_success

# Run tests matching a pattern
docker compose exec api pytest -k "cleanser"

# Run with verbose output
docker compose exec api pytest -v

# Run async tests
docker compose exec api pytest -v
```

### Database Migrations (Alembic)
```bash
# Apply all migrations
docker compose exec api alembic upgrade head

# Generate a new migration
docker compose exec api alembic revision --autogenerate -m "describe_change"

# Rollback one migration
docker compose exec api alembic downgrade -1
```

### Local Development (without Docker)
```bash
cd services/api
pip install -r requirements.txt
python -m pytest --cov=app --cov-report=term-missing
```

## Code Style Guidelines

### General
- **Python 3.12+** required
- **Type hints** mandatory for all function signatures
- **95%+ code coverage** required (configured in `.coveragerc`, fails under 95%)
- No comments unless explaining complex business logic

### Imports
```python
# Standard library first
import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session, select

# Local imports (absolute paths)
from app.core.config import settings
from app.models.event import Event, PendingEvent
from app.schemas.event import EventIngest
```

### Naming Conventions
- **Files**: `snake_case.py` (e.g., `event_model.py`, `cleanser_service.py`)
- **Classes**: `PascalCase` (e.g., `Event`, `CleansingService`, `ExtractedEvent`)
- **Functions/variables**: `snake_case` (e.g., `get_db`, `event_data`, `clean_json_ld`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `DATABASE_URL`, `MAX_RETRIES`)
- **Async functions**: prefix with `async_` if not already clear from context

### Pydantic Models (Schemas)
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    title: str
    lat: float
    lng: float
    start_time: datetime
    end_time: Optional[datetime] = None
    category: str
    hype_score: int = 0
    ticket_url: Optional[str] = None
    event_metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
```

### SQLModel Models
```python
from sqlmodel import SQLModel, Field, Column
from geoalchemy2 import Geography

class Event(EventBase, table=True):
    __tablename__ = "events"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    location: Any = Field(
        sa_column=Column(Geography(geometry_type='POINT', srid=4326))
    )
    event_metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        sa_column=Column(JSON)
    )
```

### Error Handling
```python
# Use try/except with logging for expected failures
try:
    result = await some_async_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return None  # or raise HTTPException

# Raise HTTPException for API errors
if not found:
    raise HTTPException(status_code=404, detail="Event not found")

# Use context managers for resource cleanup
with Session(engine) as session:
    result = session.exec(select(Event)).all()
```

### Async Patterns
```python
# Use async for I/O operations
async def fetch_data(url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        return response.json()

# Use asyncio.create_subprocess_exec for subprocess calls
process = await asyncio.create_subprocess_exec(
    sys.executable, script_path,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging info")
logger.info("Normal operation info")
logger.warning("Something unexpected but handled")
logger.error("Operation failed", exc_info=True)
```

### Testing Patterns
```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_function():
    # Use patch for mocking
    with patch("module.function_name", return_value=expected):
        result = await function_to_test()
    assert result == expected

# Use fixtures from conftest.py
async def test_with_client(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

## Project Architecture

### Directory Structure
```
services/api/
├── app/
│   ├── api/v1/          # API routes
│   ├── core/            # Config, settings
│   ├── db/              # Database session
│   ├── models/          # SQLModel models
│   ├── schemas/         # Pydantic schemas
│   ├── services/       # Business logic
│   └── utils/           # Utility functions
├── migrations/          # Alembic migrations
├── tests/               # Pytest tests
├── requirements.txt
├── alembic.ini
└── .coveragerc
```

### Key Technologies
- **FastAPI 0.115+** - Web framework
- **SQLModel 0.0.22** - ORM (SQLAlchemy 2.0 + Pydantic)
- **GeoAlchemy2** - PostGIS integration
- **Redis** - Caching and async task queue
- **Alembic** - Database migrations
- **Ruff** - Linting (very fast, used instead of flake8/isort)
- **Pytest** - Testing with asyncio support

## Environment Variables
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/fomo
REDIS_URL=redis://redis:6379/0
N8N_WEBHOOK_URL=http://fomo_harvester_n8n:5678/webhook/your-id
GOOGLE_API_KEY=    # Optional: for Gemini AI cleansing
MAPBOX_ACCESS_TOKEN=  # Optional: for geocoding
```
