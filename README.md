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
- **Mobile**: Expo SDK 54, React Native 0.81.5

---

## 🚀 Prerequisites

### Core (All OS)
- **Node.js 20+** & **pnpm 9+**
- **Python 3.12+** & **uv**
- **Docker Desktop**
- **Android Studio** & **JDK 21** (for mobile development). Gradle selects the JDK through your environment's `JAVA_HOME` / `PATH` — no JDK path is committed to the repo. Point `JAVA_HOME` at a JDK 21 installation.

### 🪟 Windows 11 Specifics (CRITICAL)
To support native builds and bypass long-path limits on Windows, you **MUST** have:
1.  **Ninja 1.13.2+**: Download the binary and place it exactly at `C:/ninja/ninja.exe`. Ensure it is in your System PATH.
2.  **Long Paths**: Enable via registry (`LongPathsEnabled` = 1 in `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`).
3.  **Build Flags**: Do not remove the `CMAKE_OBJECT_PATH_MAX=1024` injection found in `apps/mobile/android/build.gradle`.

---

## 💻 Local Development

See **[docs/local-development.md](./docs/local-development.md)** for the complete local setup guide.

**Windows PowerShell quick start:**

```powershell
pnpm install && uv sync --all-packages --group dev

# Start infra (postgres + redis + local portal at http://localhost:8088)
.\scripts\local-dev.ps1 infra

# Apply migrations, then run the API with hot-reload
uv run alembic -c apps/api/alembic.ini upgrade head
uv run uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000

# Verify everything is up
.\scripts\local-dev.ps1 smoke
```

**Full container mode** (builds API + dashboard from source - see GHCR note in docs if build fails):

```powershell
.\scripts\local-dev.ps1 up
```

**Local portal**: http://localhost:8088 - links to all services once infra is running.

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

Copy the example files and fill in your local values:

```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env.local
cp apps/harvester-dashboard/.env.example apps/harvester-dashboard/.env.local
cp apps/mobile/.env.example apps/mobile/.env
```

**Key rules:**
- `.env` and `.env.local` files are git-ignored — never commit them.
- Only `.env.example` files are tracked; they contain placeholders only.
- AI extraction is **disabled by default** — no API key is needed for local dev or CI.
- The Mapbox public token (`pk.*`) goes in `apps/mobile/.env` and `apps/harvester-dashboard/.env.local`.
- The Mapbox secret token (`sk.*`) for Gradle downloads belongs in `~/.gradle/gradle.properties` only — never in tracked files.
- Staging/prod credentials (Mapbox, AI API key) are injected by Jenkins credential binding, not committed to git.

For AI extraction in staging, set `AI_PROVIDER=deepseek` and `AI_API_KEY=<key>` in the root `.env`.
See `apps/api/README.md` for provider details.

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

### Mobile Build, Sync, and Device Run

**Project model:** the Android native project at `apps/mobile/android/` is **committed and hand-maintained** (it contains required Windows/monorepo fixes) — do not delete or regenerate it with `expo prebuild`. The canonical development workflow is a **local Android debug build** attached to Metro. **Expo Go is not the canonical workflow**: the app depends on native modules (`@rnmapbox/maps`, `expo-location`) that Expo Go does not include.

**Start here:** [docs/mobile/local-android-development.md](./docs/mobile/local-android-development.md) — the canonical fresh-machine-to-running-app runbook. Supporting docs: [staging-mobile-setup.md](./docs/mobile/staging-mobile-setup.md) (staging env/values) and [android-expo-debugging-guide.md](./docs/mobile/android-expo-debugging-guide.md) (troubleshooting).

Use the monorepo root for dependency sync, then run Expo from the mobile workspace:
```bash
# Root: install JS dependencies and sync Python workspace tooling
pnpm install
uv sync

# Regenerate API types consumed by mobile
pnpm --filter @fomo/api-spec build
```

#### Android
Preferred workflow when you want to rebuild native changes and choose the target device yourself:
```bash
# Root: start Metro only
pnpm --filter @fomo/mobile start
```

Then use Android Studio for the native run:
1. Open `apps/mobile/android` in Android Studio.
2. Wait for Gradle sync to finish.
3. Select the emulator or physical device you actually want from the device picker in the Android Studio toolbar.
4. Click **Run 'app'** to rebuild, install, and launch the app on that selected device.

For a physical Android device, also run:
```bash
# Verify the device is connected
adb devices

# Required for Metro connectivity on physical devices
adb reverse tcp:8081 tcp:8081
```

If you prefer the CLI path instead of Android Studio:
```bash
# Build and install the native app
pnpm --filter @fomo/mobile android
```

`pnpm --filter @fomo/mobile start` should be treated as the Metro/dev server command, not the command that chooses which Android emulator to run.

#### iOS
iOS remains a supported product target, but native iOS setup begins after the Android MVP. There is currently no committed `apps/mobile/ios/` project. When that phase begins, local iOS development will use Xcode on macOS:
```bash
# Future workflow (requires macOS + Xcode; no ios/ project exists yet)
pnpm --filter @fomo/mobile ios

# Start Expo/Metro
pnpm --filter @fomo/mobile start
```

#### Release builds & EAS status
- **EAS is not currently configured** (no `eas.json`, no EAS project). Adopting EAS is optional and deferred.
- **Production signing (Android and iOS) is deferred.** The Android `release` build type currently signs with the tracked debug keystore — any release APK built locally is for local validation only and must never be distributed or uploaded to Google Play.

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
- Never commit `.env` or `.env.local` files — they are git-ignored.
- Only `.env.example` files are tracked; they must contain placeholder values only, never real tokens.
- Real credentials (Mapbox sk.*, AI API keys) are injected at runtime — never hardcoded.
- Refer to [CORE_RULES.md](./CORE_RULES.md) for mandatory architectural standards.
- **FastAPI Python models** are the source of truth for API definitions. `packages/api-spec/openapi.json` is generated from them and must not be hand-edited.
