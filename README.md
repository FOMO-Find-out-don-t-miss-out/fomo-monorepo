# FOMO Monorepo

Welcome to the **FOMO** (Fear Of Missing Out) monorepo. This project is a highly scalable, real-time event discovery platform that combines automated web harvesting, human-in-the-loop moderation, and a high-performance FastAPI backend with spatial (PostGIS) capabilities.

## 🏗 Architecture Overview

The project is structured as a modular monorepo:

```text
.
├── apps/
│   ├── api/                   # FastAPI backend (Routing & Entry Points)
│   ├── harvester-dashboard/   # Next.js moderation dashboard
│   └── mobile/                # Expo/React Native mobile application
├── packages/
│   ├── api-spec/              # OpenAPI contract (generated from FastAPI, source of truth for TS types)
│   └── domain/                # Shared Logic (SQLModel, Services, Schemas, Utils)
├── infra/                     # Docker & Database Provisioning
├── tooling/                   # Quality & Build Scripts
├── docker-compose.yml         # Local Infrastructure Orchestration
├── pyproject.toml             # UV Workspace Configuration
├── ruff.toml                  # Strict 2026 Quality Standards
└── CORE_RULES.md              # Mandatory Developer Guidelines
```

---

## 🛠 Tech Stack 2026
This monorepo uses a modern, high-performance stack:
- **Orchestration**: Turborepo (Intelligent Build & Test Acceleration)
- **JS/TS Management**: pnpm (Fast, disk space efficient package manager)
- **Python Management**: uv (Extremely fast Python package installer and resolver)
- **API Contracts**: FastAPI → OpenAPI → openapi-typescript (Python models are source of truth)
- **Backend**: FastAPI, SQLModel, PostGIS
- **Frontend**: Next.js 16+, Tailwind, Shadcn UI
- **Mobile**: Expo 55+, React Native 0.81.5+

---

## 🚀 Prerequisites

### Core (All OS)
- **Node.js 20+** & **pnpm 9+**
- **Python 3.12+** & **uv**
- **Docker Desktop**
- **Android Studio** & **JDK 17** (for mobile development)

### 🪟 Windows 11 Specifics (CRITICAL)
To support native builds and bypass long-path limits on Windows, you **MUST** have:
1.  **Ninja 1.13.2+**: Download the binary and place it exactly at `C:/ninja/ninja.exe`. Ensure it is in your System PATH.
2.  **Long Paths**: Enable via registry (`LongPathsEnabled` = 1 in `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`).
3.  **Build Flags**: Do not remove the `CMAKE_OBJECT_PATH_MAX=1024` injection found in `apps/mobile/android/build.gradle`.

---

## ✅ Getting Started (First-Time Setup)

### 1. Bootstrap
Run these commands from the root directory:
```bash
# Install JS/TS dependencies and link workspaces
pnpm install

# Sync Python dependencies
uv sync

# Verify the stack (runs lint, test, and schema checks)
pnpm check-quality
```

### 2. Environment Configuration
Create a `.env` file in the root directory (and copy relevant keys to `apps/api/.env` and `apps/mobile/.env`):
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fomo
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/fomo
MAPBOX_ACCESS_TOKEN=your_mapbox_pk_token
GOOGLE_API_KEY=your_gemini_api_key
N8N_WEBHOOK_URL=http://fomo_harvester_n8n:5678/webhook/your-id

# Mobile Specific (in apps/mobile/.env)
EXPO_PUBLIC_MAPBOX_TOKEN=pk.your_public_token
```
*Note: For Mapbox Gradle downloads, place your secret `sk.*` token in `~/.gradle/gradle.properties`.*

### 3. Spin up the Infrastructure
```bash
# Start containers
docker compose up -d --build

# Apply database migrations
docker compose exec api alembic upgrade head

# Hydrate local data
pnpm db:seed
```

### 4. Verify the Installation
- **Moderation Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **n8n Dashboard**: [http://localhost:5678](http://localhost:5678)
- **PostgreSQL**: Accessible at `localhost:5432` from your host machine.

---

## 🛠 Development Workflows

### Running Workspaces Locally
- **API**: `pnpm --filter @fomo/api dev`
- **Dashboard**: `pnpm --filter @fomo/harvester-dashboard dev`
- **Mobile (Expo)**: `adb reverse tcp:8081 tcp:8081` then `pnpm --filter @fomo/mobile start`

### Database Migrations (Alembic)
When you modify models in `packages/domain/models/`:
1. **Generate**: `docker compose exec api alembic revision --autogenerate -m "description"`
2. **Apply**: `docker compose exec api alembic upgrade head`

### Database Hydration
- **Seed**: `pnpm db:seed` (Imports from `infra/seeds/`)
- **Dump**: `pnpm db:dump` (Exports live data to `infra/seeds/` for versioning)

### Data Pipeline (Harvester)
Trigger internal services via the API:
```bash
# Trigger Scraper
curl -X POST http://localhost:8000/api/v1/ingestion/run-scraper

# Trigger Batch Geocoding
curl -X POST http://localhost:8000/api/v1/ingestion/batch-geocode
```

---

## 🤖 AI & Tooling

### MCP Awareness (Infrastructure Bridge)
This repo supports the **Model Context Protocol (MCP)**. Config: `infra/mcp-config.json`.
Allows AI agents to connect directly to the live PostgreSQL database to inspect schemas and constraints in real-time.

### Quality Gates
We enforce strict standards via `pnpm check-quality`:
- **Linting**: Ruff (Python), ESLint (JS/TS).
- **Type Safety**: Strict TypeScript (types generated from FastAPI OpenAPI spec via openapi-typescript).
- **Coverage**: Minimum **95% code coverage** is enforced.
- **Generated API Artifact Verification**: `pnpm --filter @fomo/api-spec verify-schema` runs `uv run python tooling/verify-generated-api-artifacts.py`, regenerates `openapi.json` and frontend `api.generated.ts` files, then fails if Git detects drift in those tracked generated artifacts.

---

## 🔍 Troubleshooting (The "Golden List")

### Windows Native Build Failures
- **Manifest 'build.ninja' still dirty**: Ensure you are using Ninja 1.13.2+ located at `C:/ninja/ninja.exe`. Standard CMake-bundled Ninja often fails with Windows path lengths.
- **Path too long**: Verify `LongPathsEnabled` is 1 and the `subprojects` block in `apps/mobile/android/build.gradle` is applying the `CMAKE_OBJECT_PATH_MAX` flag.

### Mobile & Metro
- **White/Red screen on phone**: Metro is likely unreachable. Run `adb reverse tcp:8081 tcp:8081`.
- **Mapbox token errors**: Ensure `EXPO_PUBLIC_MAPBOX_TOKEN` is in `apps/mobile/.env` AND the secret token is in your global `gradle.properties`.
- **`adb devices` empty**: Check USB drivers, MTP mode, and accept the RSA fingerprint prompt on the device.

### Docker & Python
- **Build Context Error**: All Docker commands **MUST** be run from the monorepo root. Building from `apps/api/` will fail to find `packages/domain`.
- **`/dev/null` error**: If `uv sync` fails in Docker, ensure `ENV UV_NO_PROGRESS=1` is set in the Dockerfile.
- **Schema Drift Detected**: Your SQLModel definitions don't match the DB. Run migrations (`alembic revision --autogenerate`) to sync.

### General
- **Turbo Cache Poisoning**: If changes aren't reflecting, run `pnpm turbo run <task> --force` or delete the `.turbo` folders.
- **uv lock conflict**: If dependencies are wonky, run `uv lock --upgrade` or delete `uv.lock` and re-run `uv sync`.

---

## 🔒 Security & Rules
- Never commit `.env` files.
- Refer to [CORE_RULES.md](./CORE_RULES.md) for mandatory architectural standards.
- **FastAPI Python models** are the source of truth for API definitions. `packages/api-spec/openapi.json` is generated from them and must not be hand-edited.
