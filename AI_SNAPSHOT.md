# AI Context Snapshot (2026 standards)

## 📁 Directory Tree (Max Depth: 3)
```text
fomo-monorepo/
├───.claude/
│   └───settings.local.json
├───.github/
│   └───workflows/
│   │   └───main.yml
├───.idea/
│   ├───dataSources/
│   │   ├───3d7fad17-632b-4e76-86f7-7a92f1d6664b/
│   │   ├───3d7fad17-632b-4e76-86f7-7a92f1d6664b.xml
│   │   └───data_sources_history.xml
│   ├───inspectionProfiles/
│   │   └───profiles_settings.xml
│   ├───.gitignore
│   ├───dataSources.local.xml
│   ├───dataSources.xml
│   ├───fomo-monorepo.iml
│   ├───misc.xml
│   ├───modules.xml
│   ├───vcs.xml
│   └───workspace.xml
├───apps/
│   ├───api/
│   │   ├───app/
│   │   ├───migrations/
│   │   ├───tests/
│   │   ├───.coverage
│   │   ├───.coveragerc
│   │   ├───.env
│   │   ├───alembic.ini
│   │   ├───Dockerfile
│   │   ├───package.json
│   │   ├───pyproject.toml
│   │   └───requirements.txt
│   ├───harvester-dashboard/
│   │   ├───app/
│   │   ├───components/
│   │   ├───hooks/
│   │   ├───lib/
│   │   ├───public/
│   │   ├───styles/
│   │   ├───types/
│   │   ├───.dockerignore
│   │   ├───.gitignore
│   │   ├───components.json
│   │   ├───Dockerfile
│   │   ├───eslint.config.mjs
│   │   ├───next-env.d.ts
│   │   ├───next.config.mjs
│   │   ├───package.json
│   │   ├───pnpm-lock.yaml
│   │   ├───postcss.config.mjs
│   │   ├───tsconfig.json
│   │   └───tsconfig.tsbuildinfo
│   └───mobile/
│   │   ├───.expo/
│   │   ├───android/
│   │   ├───app/
│   │   ├───components/
│   │   ├───types/
│   │   ├───.env
│   │   ├───.gitignore
│   │   ├───app.json
│   │   ├───babel.config.js
│   │   ├───eslint.config.js
│   │   ├───global.css
│   │   ├───metro.config.js
│   │   ├───nativewind-env.d.ts
│   │   ├───package.json
│   │   ├───tailwind.config.js
│   │   ├───tsconfig.json
│   │   └───tsconfig.json.lRPRMCiDQwoFK9sZh0mFMYTY3UVAxw_O4GRZCs7yYqE
├───docs/
│   └───infrastructure/
│   │   └───mcp-setup.md
├───infra/
│   ├───postgres/
│   │   └───init-db.sh
│   ├───seeds/
│   │   ├───events.json
│   │   ├───pending_events.json
│   │   └───venues.json
│   └───mcp-config.json
├───packages/
│   ├───api-spec/
│   │   ├───openapi.json
│   │   └───package.json
│   ├───domain/
│   │   ├───domain.egg-info/
│   │   ├───models/
│   │   ├───resources/
│   │   ├───schemas/
│   │   ├───services/
│   │   ├───tests/
│   │   ├───utils/
│   │   ├───__init__.py
│   │   ├───package.json
│   │   └───pyproject.toml
│   └───__init__.py
├───tooling/
│   ├───check-quality.ps1
│   ├───check-quality.sh
│   ├───db-hydrate.py
│   ├───debug_geocoder.py
│   ├───generate-context.py
│   ├───generate-frontend-types.mjs
│   └───verify-schema-sync.py
├───.coverage
├───.dockerignore
├───.env
├───.gitignore
├───AGENTS.md
├───AI_SNAPSHOT.md
├───CLAUDE.md
├───CORE_RULES.md
├───docker-compose.yml
├───GEMINI.md
├───opencode.json
├───package.json
├───pnpm-lock.yaml
├───pnpm-workspace.yaml
├───pyproject.toml
├───README.md
├───ruff.toml
├───turbo.json
└───uv.lock
```

## 🛣 API Routes (v1)
### events.py
- GET `/discovery` -> `get_events_discovery`
### health.py
- GET `/health` -> `health_check`
### ingestion.py
- POST `/ingest` -> `ingest_events`
- POST `/approve/{pending_id}` -> `approve_event`
- DELETE `/cleanup-pending` -> `cleanup_pending_events`
- DELETE `/reject/{pending_id}` -> `reject_event`
- POST `/run-scraper` -> `trigger_scraper`
- POST `/batch-geocode` -> `trigger_batch_geocode`
### moderation.py
- GET `/pending-events` -> `get_pending_events`
- GET `/events` -> `get_published_events`
- POST `/events/{event_id}/unpublish` -> `unpublish_event`
- PATCH `/events/{event_id}` -> `update_published_event`
- PATCH `/pending-events/{event_id}` -> `update_pending_event`
- POST `/pending-events/{event_id}/approve` -> `approve_event`
- POST `/pending-events/{event_id}/reject` -> `reject_event`
- POST `/pending-events/approve-batch` -> `approve_events_batch`
- POST `/pending-events/reject-batch` -> `reject_events_batch`
- POST `/pending-events/{event_id}/occurrences` -> `add_occurrence`
- GET `/venues` -> `get_venues`
- PATCH `/venues/{venue_id}` -> `update_venue`
- DELETE `/venues/{venue_id}` -> `delete_venue`
- POST `/venues/merge` -> `merge_venues`
- POST `/batch-update-location` -> `batch_update_location`
- GET `/geocode/suggestions` -> `get_geocode_suggestions`

## 🏗 OpenAPI Schemas (packages/api-spec/openapi.json)
- `BatchApproveRequest`
- `BatchRejectRequest`
- `EventBase`
- `EventDiscoveryResponse`
- `EventIngest`
- `GeocodeResult`
- `HTTPValidationError`
- `IngestSummary`
- `LocationBatchUpdate`
- `OccurrenceCreate`
- `PendingEventResponse`
- `PendingEventUpdate`
- `ValidationError`
- `Venue`
- `VenueMergeRequest`
- `VenueUpdate`

Total endpoints: 24

## 🧪 Quality & Coverage Status
- `.coverage` file present (95% target enforced).
- Linting: Ruff (Python), ESLint (TS/JS).
- Validation: FastAPI → openapi.json → openapi-typescript pipeline.
