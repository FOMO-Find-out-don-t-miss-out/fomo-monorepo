# FOMO Monorepo: Gemini CLI Context

This document provides essential context for the **FOMO (Fear Of Missing Out)** project, a real-time event discovery platform. Use these guidelines and architectural insights to ensure all contributions are consistent with existing standards.

---

## 🏗 Project Overview

FOMO is a highly scalable platform that aggregates event data through automated harvesting, processes it using AI, and serves it via a high-performance FastAPI backend to a mobile application.

### Core Stack
- **Backend**: FastAPI with [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy 2.0 + Pydantic).
- **Database**: PostgreSQL with [PostGIS](https://postgis.net/) for spatial queries.
- **AI/Extraction**: [Gemini 1.5/2.5 Flash](https://ai.google.dev/) via `instructor` for unstructured data parsing.
- **Workflow**: [n8n](https://n8n.io/) for scraper orchestration.
- **Infrastructure**: Docker Compose, Redis (caching/task queue).
- **Mobile**: Expo / React Native (TypeScript).

---

## 📁 Repository Structure

```text
.
├── apps/mobile            # Expo/React Native mobile application
├── apps/harvester-dashboard # Next.js moderation dashboard (React)
├── infra/                 # Docker, database initialization, and config
├── services/api           # FastAPI backend (Core service)
│   ├── app/
│   │   ├── api/           # API Endpoints (v1/health, v1/internal)
│   │   ├── core/          # Configuration (config.py)
│   │   ├── db/            # Database session management
│   │   ├── models/        # SQLModel entities (Event, User, Venue)
│   │   ├── schemas/       # Pydantic schemas for request/response
│   │   ├── services/      # Business logic (Harvester, Geocoder, Cleanser)
│   │   └── utils/         # Helpers (datetime, etc.)
│   ├── migrations/        # Alembic database migrations
│   └── tests/             # Pytest suite (Unit & Integration)
└── docker-compose.yml     # Orchestration for local development
```

---

## 🚀 Building & Running

### Local Environment Setup
1. **Initialize Containers**:
   ```bash
   docker compose up -d --build
   ```
2. **Apply Migrations**:
   ```bash
   docker compose exec api alembic upgrade head
   ```
3. **Seed/Trigger Scraper** (Manual):
   ```bash
   curl -X POST http://localhost:8000/api/v1/internal/run-scraper
   ```

### Access Points
- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **n8n**: [http://localhost:5678](http://localhost:5678)

---

## 🛠 Development Workflows

### Database & Models
- **Adding Models**: All models must inherit from `SQLModel`. Spatial data uses `Geography` columns via `GeoAlchemy2`.
- **Migrations**: Always use Alembic.
  ```bash
  docker compose exec api alembic revision --autogenerate -m "description"
  docker compose exec api alembic upgrade head
  ```

### Data Pipeline (Harvester)
- **Cleansing**: `CleansingService` (in `services/api/app/services/harvester/cleanser.py`) uses `google-generativeai` to extract structured `ExtractedEvent` from HTML noise.
- **Geocoding**: `GeocoderService` uses Mapbox to resolve location names.
- **Moderation**: 
  - New events land in `pending_events`. 
  - Use the **Harvester Dashboard** (React) to approve, reject, or edit events.
  - Moderation API: `v1/moderation` handles pending events, published events, and venue management.
  - Events move from `pending_events` to the live `events` table upon approval.

---

## 🧪 Testing & Quality Standards

The project enforces a **95% minimum code coverage** threshold.

- **Run All Tests**:
  ```bash
  docker compose exec api pytest
  ```
- **Coverage Report**:
  ```bash
  docker compose exec api pytest --cov=app --cov-report=term-missing
  ```
- **Linting & Formatting**: We use **Ruff**. Always run it before committing.
  ```bash
  docker compose exec api ruff check .
  docker compose exec api ruff format .
  ```

---

## 💡 Implementation Notes

- **Spatial Queries**: When querying locations, always use PostGIS functions (e.g., `ST_DWithin`).
- **Date Handling**: All timestamps are stored as UTC. Use `DateTimeHelper` for parsing.
- **AI Integration**: Ensure the `GOOGLE_API_KEY` is set in `.env` for the cleanser to function.
- **Environment Variables**: Managed in `app/core/config.py` via `Pydantic-Settings`.
