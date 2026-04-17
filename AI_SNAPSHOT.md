# AI Context Snapshot (2026 standards)

## 🎯 CURRENT PHASE: 2 (Data & Schema Sync)
- **Phase 1 (Native Infra) COMPLETE**: Windows 11 build loop stable with Ninja 1.13.2 @ `C:/ninja/ninja.exe` and `CMAKE_OBJECT_PATH_MAX=1024` fix in `apps/mobile/android/build.gradle`.
- **Phase 2 Objective**: Verify end-to-end schema sync: `TypeSpec` (Source) -> `packages/domain` (Models) -> `PostgreSQL` (Alembic).

## 📁 Key Workspaces
- `apps/api`: FastAPI, SQLModel, Geocoder, Harvester Orchestrator.
- `apps/mobile`: Expo 55, RN 0.81.5, Mapbox integration.
- `packages/api-spec`: TypeSpec definitions (Source of Truth).
- `packages/domain`: Shared Pydantic/SQLModel logic.

## 🛣 API Routes (v1 Summary)
- `/health`: System health.
- `/ingestion/run-scraper`: Manual harvester trigger.
- `/moderation/pending-events`: Moderation queue management.
- `/moderation/venues`: Venue management & merging.
- `/moderation/geocode/suggestions`: Mapbox suggestions.

## 🏗 Infrastructure State
- **Docker**: `api`, `db` (PostGIS), `redis`, `dashboard`, `n8n` active.
- **Database**: Migrations applied up to `head`. Seeding functional via `pnpm db:seed`.
- **Mobile**: Metro reachable via `adb reverse tcp:8081 tcp:8081`. Mapbox tokens required in `.env` (pk.*) and `gradle.properties` (sk.*).

## 🧪 Quality Gates
- **Lint**: Ruff (Strict), ESLint.
- **Coverage**: 95% minimum enforced.
- **Sync**: `verify-schema-sync.py` checks TypeSpec vs live DB.

## 📁 Directory Tree (Max Depth: 2)
```text
fomo-monorepo/
├── apps/
│   ├── api/                   # Backend
│   ├── harvester-dashboard/   # Admin UI
│   └── mobile/                # Expo App
├── packages/
│   ├── api-spec/              # TypeSpec (Truth)
│   └── domain/                # Shared Logic
├── infra/                     # DB & MCP Config
├── tooling/                   # Quality Scripts
└── CORE_RULES.md              # Mandatory Guidelines
```
