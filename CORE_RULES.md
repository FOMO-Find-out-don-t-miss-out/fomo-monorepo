# FOMO Monorepo: CORE RULES (2026 Industry Standards)

This document is the absolute source of truth for all development in the FOMO project. All agents and developers must strictly adhere to these rules.

---

## 🏛 1. ARCHITECTURAL HIERARCHY
Maintain strict separation of concerns across the monorepo to ensure scalability and prevent circular dependencies.

- **APPS (`apps/*`)**: Can depend on **PACKAGES**. These are deployment targets (e.g., `apps/api`, `apps/mobile`).
- **PACKAGES (`packages/*`)**: Shared libraries and core logic. **PACKAGES MUST NOT depend on APPS** (Circular dependency violation).
- **DOMAIN LOGIC**: All business logic, including Pydantic models (Schemas), SQLModel definitions (Models), Services, and cross-package Utilities, **MUST** reside in `packages/domain`.
- **API ENTRY POINTS**: `apps/api` is strictly for routing, dependency injection, and HTTP-related entry points. No business logic is allowed in `apps/api`.

---

## 🏗 MONOREPO INTEGRITY (Mandatory)
To ensure shared packages are correctly resolved during containerization and deployment:

1.  **ROOT BUILD CONTEXT**: All Docker builds **MUST** use the monorepo root as the context.
2.  **WORKSPACE PRESERVATION**: Dockerfiles must copy the root `pyproject.toml` and `uv.lock` before installing any package-specific dependencies.
3.  **CMD EXECUTION**: Applications should be executed from the root using `--app-dir` or similar flags to allow the runtime to resolve workspace-local dependencies.

---

## 🤖 2. AI AGENT WORKING LOOP (Mandatory)
Every coding task performed by an AI agent must follow this iterative cycle:

1.  **CONTEXT-FIRST**: At the start of every session, the Agent **MUST** ask the user to run `pnpm context` and read `AI_SNAPSHOT.md` to align its internal state with minimum token usage.
2.  **PLAN**: Output a concise Markdown strategy before any code modification.
3.  **TEST**: Write a failing **Pytest** case that reproduces the issue or defines the new feature's behavior.
4.  **EXECUTE**: Implement the minimal code required to make the test pass.
5.  **VERIFY**: Run `uv run ruff check .` for linting and `pytest` for verification.

**LITMUS TEST**: Before proposing any database migration or SQLModel change, the Agent **MUST** use the MCP Bridge to inspect the current state of the PostgreSQL schema. Proposing changes based on stale context is forbidden.

---

## 🧪 3. QUALITY GATES
- **CACHED VALIDATION**: Local development must use `turbo` (e.g., `pnpm check-quality`) to ensure only affected parts of the monorepo are tested, preserving developer flow state.
- **COMMAND INTEGRITY**: Never use `npm` or `pip`. Use `pnpm` for Node tasks and `uv` for Python tasks. Any generated code that includes `package-lock.json` or `requirements.txt` (unless for Docker base) will be rejected.
- **95% Minimum Code Coverage**: Enforced for every new feature and bug fix.
- **Linting**: All Python code must pass `uv run ruff check .` and `uv run ruff format .` before completion.
- **Imports**: Use **absolute imports only** (e.g., `from packages.domain.models import Event`). Relative imports are strictly forbidden.
- **Type Hints**: Mandatory for all function signatures and public variables.

---

## 📦 4. DEPENDENCY CONTROL
- **Strict Stack**: Do not add new libraries without explicit justification. Use the existing stack:
  - **Backend**: FastAPI, SQLModel (SQLAlchemy 2.0), Pydantic v2, GeoAlchemy2.
  - **Infrastructure**: Redis, PostgreSQL/PostGIS.
  - **Frontend**: React, Next.js, Tailwind, Shadcn UI.
- **Unified Tooling**: Use `uv` for all Python dependency management and script execution.

---

## 🛠 Development Workflows

### Database & Migrations
- All models inherit from `SQLModel` and reside in `packages/domain`.
- Use Alembic for migrations:
  ```bash
  docker compose exec api alembic revision --autogenerate -m "description"
  docker compose exec api alembic upgrade head
  ```
- **DATABASE MANAGEMENT**:
  - **DATA CONSISTENCY**: When switching machines, always run 'pnpm db:seed' after migrations to ensure local environment parity. Do not commit large production datasets to the seeds folder.

- **SYNC LOCK**: No PR shall be merged if the `verify-schema-sync` check fails. Any Python model change MUST be followed by a generated Alembic migration in the same commit, and `pnpm --filter @fomo/api-spec build` must be re-run to keep `openapi.json` and generated TypeScript types in sync.

### Schema Sync Workflow
- Run `python tooling/verify-schema-sync.py` before pushing backend contract changes. This is the manual pre-commit gate until a repo-level pre-commit framework is introduced.
- `verify-schema-sync.py` checks four things only: ORM metadata vs the live DB, FastAPI path/method and named-schema coverage vs committed `packages/api-spec/openapi.json`, freshness of generated frontend API types, and mobile category alias coherence vs the backend enum.
- `pnpm --filter @fomo/api-spec build` regenerates `packages/api-spec/openapi.json` plus both frontend `api.generated.ts` files. Do not hand-edit generated artifacts.
- `pnpm turbo run check-quality --force` is the authoritative CI-equivalent local verification. `@fomo/api` must execute `verify-schema-sync.py` inside its own `check-quality`, and `@fomo/api-spec` must rebuild generated artifacts and fail if Git shows drift afterward.

### Data Pipeline (Harvester)
- **Extraction**: Modular extractors (JSON-LD, AI/LLM via Gemini/Instructor) in `apps/api/app/services/harvester/cleansing/`.
- **Classification**: Business logic for taxonomy and tagging MUST reside in `packages/domain/services/event_classifier.py`.
- **Orchestration**: `CleansingService` (orchestrator) coordinates extraction, domain-driven classification, and geocoding.
- **Geocoding**: Mapbox-based location resolution via `GeocoderService`.
- **Moderation**: Events flow from `pending_events` (moderation) to `events` (live) via the dashboard.

## 🪟 WINDOWS NATIVE INFRASTRUCTURE (Phase 1 Fixes)
To prevent "build.ninja is dirty" and long-path errors on Windows 11:
1.  **NINJA**: Must use custom Ninja 1.13.2 at `C:/ninja/ninja.exe`.
2.  **LONG PATHS**: `apps/mobile/android/build.gradle` contains a `subprojects` block that injects `CMAKE_OBJECT_PATH_MAX=1024` into all native subprojects. Do not remove this.
3.  **WORKLETS**: Reanimated v4 worklets-dir is resolved via `node require.resolve` in the root `build.gradle` to bypass pnpm isolation issues.

## 🛠 COMMANDS & WORKFLOWS
- **Python**: Always use `uv sync`. Never `pip`.
- **Node**: Always use `pnpm install`. Never `npm` or `yarn`.
- **API Spec**: `packages/api-spec` is the source of truth. Regenerate via `pnpm --filter @fomo/api-spec build`.
- **Mobile**:
  - Run from `apps/mobile/android` using `./gradlew`.
  - For physical devices: `adb reverse tcp:8081 tcp:8081` is mandatory for Metro connectivity.
  - Mapbox: `EXPO_PUBLIC_MAPBOX_TOKEN` (pk.*) in `.env` AND `sk.*` token in `~/.gradle/gradle.properties`.

---

## 💡 Implementation Notes
- **Spatial Queries**: Always use PostGIS functions (e.g., `ST_DWithin`).
- **Date Handling**: Store all timestamps as UTC.
- **Async Patterns**: Use `async`/`await` for all I/O operations.
