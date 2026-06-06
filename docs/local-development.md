# Local Development Guide

This guide helps a new developer run the FOMO API and dashboard locally with an environment close to staging.

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Docker Desktop | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled with Docker Desktop) | - |
| Python | 3.12+ | https://www.python.org/ |
| uv | latest | `pip install uv` or https://docs.astral.sh/uv/ |
| Node.js | 20+ | https://nodejs.org/ |
| pnpm | 10+ | `npm install -g pnpm` |

### Windows 11 extras
See [CORE_RULES.md](../CORE_RULES.md) for Ninja 1.13.2+ and long-path requirements (mobile only; not needed for API/dashboard local dev).

---

## One-command setup (Windows PowerShell)

```powershell
# Install dependencies
pnpm install
uv sync --all-packages --group dev

# Copy env examples (needed for host-mode dev only; not required for container mode)
Copy-Item apps/api/.env.example apps/api/.env.local
Copy-Item apps/harvester-dashboard/.env.example apps/harvester-dashboard/.env.local

# Start infrastructure (postgres + redis + local portal)
.\scripts\local-dev.ps1 infra

# Apply database migrations
uv run alembic -c apps/api/alembic.ini upgrade head

# Run API on the host (fast reloads, recommended for active development)
uv run uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
```

Or to run everything in containers (see GHCR note below before running):

```powershell
.\scripts\local-dev.ps1 up
```

---

## Quick-reference: local-dev.ps1 commands

```powershell
.\scripts\local-dev.ps1 infra   # Start postgres, redis, local-portal (no build)
.\scripts\local-dev.ps1 up      # Build + start full container stack
.\scripts\local-dev.ps1 app     # Alias for 'up'
.\scripts\local-dev.ps1 n8n     # Start n8n optional profile
.\scripts\local-dev.ps1 smoke   # Run smoke tests
.\scripts\local-dev.ps1 down    # Stop all services
.\scripts\local-dev.ps1 reset   # Wipe volumes + restart infra
.\scripts\local-dev.ps1 urls    # Print all local service URLs
```

Bash equivalent (Linux/macOS/Git Bash): `bash scripts/local-dev.sh <command>`

---

## Local portal

After starting infra, open **http://localhost:8088** for a local dashboard with links to all services.

The portal is a static HTML page served by `nginx:1.27-alpine`. It requires no credentials and starts alongside postgres/redis when you run `infra` or `up`.

---

## Service URLs

| Service | URL |
|---|---|
| Local portal | http://localhost:8088 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Health | http://localhost:8000/api/v1/health |
| API Metrics | http://localhost:8000/metrics |
| Dashboard | http://localhost:3000 |
| n8n (optional) | http://localhost:5678 |
| Postgres | localhost:5432 (user: `fomo` / db: `fomo`) |
| Redis | localhost:6379 |

---

## GHCR authentication error (API build troubleshooting)

When running `.\scripts\local-dev.ps1 up` or `docker compose -f docker-compose.local.yml build`, the API builder stage pulls:

```
ghcr.io/astral-sh/uv:python3.12-bookworm-slim
```

If you see:

```
failed to fetch oauth token: denied
```

This means Docker is authenticated to GHCR with a credential that does not have pull access to this public package. Fix:

```powershell
# 1. Log out of GHCR so Docker uses anonymous access
docker logout ghcr.io

# 2. Confirm the image is publicly pullable
docker pull ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 3. Retry the build
.\scripts\local-dev.ps1 up
```

The `ghcr.io/astral-sh/uv` image is public and does not require authentication. The error occurs only when a stale or scoped GHCR token blocks anonymous fallback.

> **Alternative while waiting for the image pull**: use host-mode API dev (infra + `uv run uvicorn ...`) - this bypasses Docker image builds entirely and works immediately.

---

## Running modes

### Mode 1 - Host API (recommended for active backend development)

Start infra in containers, run API directly for fast reloads:

```powershell
# Start infra
.\scripts\local-dev.ps1 infra

# Run API on host
uv run uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
```

Requires `apps/api/.env.local` with `DATABASE_URL` pointing to `localhost:5432`.

### Mode 2 - Full container mode (smoke testing / onboarding verification)

Builds and starts all services from local source. Requires the GHCR pull to succeed (see above):

```powershell
.\scripts\local-dev.ps1 up
# or
docker compose -f docker-compose.local.yml up --build
```

### Mode 3 - Host dashboard (recommended for active frontend development)

```powershell
# Start infra + API (in any mode above), then:
pnpm --filter @fomo/harvester-dashboard dev
```

Requires `apps/harvester-dashboard/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`.

---

## First-time setup (step by step)

### 1. Clone and install dependencies

```powershell
git clone <repo-url>
cd fomo-monorepo

pnpm install
uv sync --all-packages --group dev
```

### 2. Copy env examples

```powershell
Copy-Item apps/api/.env.example          apps/api/.env.local
Copy-Item apps/harvester-dashboard/.env.example  apps/harvester-dashboard/.env.local
```

No root `.env` file is required when using `docker-compose.local.yml`. All local defaults are hardcoded in that file.

### 3. Start local infrastructure

```powershell
.\scripts\local-dev.ps1 infra
```

Postgres and Redis are ready when both show `healthy` in `docker compose -f docker-compose.local.yml ps`.

### 4. Apply database migrations

```powershell
# From the host (requires apps/api/.env.local and postgres running)
uv run alembic -c apps/api/alembic.ini upgrade head

# Or from inside the API container (full container mode)
docker compose -f docker-compose.local.yml exec api alembic -c apps/api/alembic.ini upgrade head
```

### 5. Verify

```powershell
.\scripts\local-dev.ps1 smoke
```

Expected healthy output:

```
==> Running smoke tests

  PASS  API docs (Swagger)              -> HTTP 200
  PASS  API health                      -> HTTP 200
  PASS  Dashboard                       -> HTTP 200
  PASS  Local portal                    -> HTTP 200

  4 passed, 0 failed - all checks OK
```

---

## Optional: n8n scraping automation

n8n is not required for API or dashboard development. Start it only when working on harvester workflows:

```powershell
.\scripts\local-dev.ps1 n8n
# or
docker compose -f docker-compose.local.yml --profile n8n up -d
```

n8n will be available at http://localhost:5678. Its database (`n8n__harvester`) is created automatically when postgres first initialises.

To stop n8n:

```powershell
docker compose -f docker-compose.local.yml --profile n8n stop n8n
```

> Staging n8n deployment is a separate follow-up and is not configured here.

---

## Smoke tests

```powershell
# PowerShell script (recommended)
.\scripts\local-dev.ps1 smoke

# Manual PowerShell
Invoke-WebRequest http://localhost:8000/docs -Method HEAD -UseBasicParsing
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-WebRequest http://localhost:3000 -Method HEAD -UseBasicParsing
Invoke-WebRequest http://localhost:8088 -Method HEAD -UseBasicParsing
docker compose -f docker-compose.local.yml ps

# Bash (Git Bash / WSL / Linux/macOS)
bash scripts/local-smoke-test.sh
```

---

## AI extraction

AI extraction is **disabled by default**. No API key is required for local development or CI.

```
AI_EXTRACTION_ENABLED=false
AI_PROVIDER=disabled
```

The harvesting pipeline will not call any paid AI provider. All automated tests also block external AI calls via the safety guard in `apps/api/tests/conftest.py` (FOMO-131).

### Enabling AI manually (opt-in, costs money)

Only do this if you are explicitly testing AI extraction. Edit `apps/api/.env.local`:

```
AI_EXTRACTION_ENABLED=true
AI_PROVIDER=deepseek
AI_API_KEY=your-deepseek-api-key-here
```

Then restart the API. See `apps/api/README.md` for provider details and cost controls.

---

## Mapbox (optional)

Mapbox is optional for local development:

- **API geocoding**: only needed if testing geocoding. Uncomment and set `MAPBOX_ACCESS_TOKEN` in `apps/api/.env.local`.
- **Dashboard map tiles**: only needed if testing map UI. Uncomment and set `NEXT_PUBLIC_MAPBOX_TOKEN` in `apps/harvester-dashboard/.env.local`.

Never commit real Mapbox tokens. The `.gitignore` ensures `.env.local` files are never tracked.

---

## Resetting from scratch

```powershell
.\scripts\local-dev.ps1 reset
# (confirms before wiping volumes)

# Then re-run migrations:
uv run alembic -c apps/api/alembic.ini upgrade head
```

Manual equivalent:

```powershell
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d postgres redis local-portal
uv run alembic -c apps/api/alembic.ini upgrade head
```

---

## Running tests

All tests run without credentials or paid services:

```powershell
# Full Python test suite
uv run pytest apps/api/tests/

# With linting
uv run ruff check apps/api/app apps/api/tests
uv run ruff format --check apps/api/app apps/api/tests

# Full quality gate (lint + test + schema checks via turbo)
pnpm check-quality
```

---

## Differences from staging

| Area | Local | Staging |
|---|---|---|
| Postgres | postgis/postgis:18-3.6 | postgis/postgis:18-3.6 |
| Redis | redis:8.6.4-alpine | redis:8.6.4-alpine |
| Orchestration | Docker Compose | Kubernetes + ArgoCD |
| Ingress / TLS | None (plain HTTP) | Traefik + cert-manager |
| CI/CD | Manual | Jenkins |
| Observability | None | Prometheus, Loki, Jaeger |
| Database state | Empty (seed with `pnpm db:seed`) | Populated |
| n8n | Optional profile | Separate deployment (follow-up) |
| AI extraction | Disabled | DeepSeek (when enabled) |
| Secrets | Placeholder values | Jenkins credential binding |

---

## Service versions

| Service | Local | Staging reference |
|---|---|---|
| Postgres/PostGIS | postgis/postgis:18-3.6 | postgis/postgis:18-3.6 |
| Redis | redis:8.6.4-alpine | redis:8.6.4-alpine |
| API | Built from local source | ghcr.io/fomo-find-out-don-t-miss-out/fomo-api:2eecedd |
| Dashboard | Built from local source | ghcr.io/fomo-find-out-don-t-miss-out/fomo-harvester-dashboard:b7bd5f3 |
| n8n | n8nio/n8n:2.25.5 (pinned) | Separate deployment |
| Local portal | nginx:1.27-alpine | n/a (local only) |
