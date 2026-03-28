# FOMO Monorepo: CORE RULES (2026 Industry Standards)

This document is the absolute source of truth for all development in the FOMO project. All agents and developers must strictly adhere to these rules.

---

## 🏛 1. ARCHITECTURAL HIERARCHY
Maintain strict separation of concerns across the monorepo to ensure scalability and prevent circular dependencies.

- **APPS (`apps/*`)**: Can depend on **PACKAGES**. These are deployment targets (e.g., `apps/api`, `apps/mobile`).
- **PACKAGES (`packages/*`)**: Shared libraries and core logic. **PACKAGES MUST NOT depend on APPS** (Circular dependency violation).
- **DOMAIN LOGIC**: All business logic, including Pydantic models (Schemas), SQLModel definitions (Models), and Services, **MUST** reside in `packages/domain`.
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

1.  **PLAN**: Output a concise Markdown strategy before any code modification.
2.  **TEST**: Write a failing **Pytest** case that reproduces the issue or defines the new feature's behavior.
3.  **EXECUTE**: Implement the minimal code required to make the test pass.
4.  **VERIFY**: Run `uv run ruff check .` for linting and `pytest` for verification.

**LITMUS TEST**: Before proposing any database migration or SQLModel change, the Agent **MUST** use the MCP Bridge to inspect the current state of the PostgreSQL schema. Proposing changes based on stale context is forbidden.

---

## 🧪 3. QUALITY GATES
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
- **SYNC LOCK**: No PR shall be merged if the `verify-schema-sync` check fails. Any change to TypeSpec MUST be followed by a generated Alembic migration in the same commit.

### Data Pipeline (Harvester)
- **Cleansing**: Gemini-powered extraction via `instructor`.
- **Geocoding**: Mapbox-based location resolution.
- **Moderation**: Events flow from `pending_events` (moderation) to `events` (live) via the dashboard.

---

## 💡 Implementation Notes
- **Spatial Queries**: Always use PostGIS functions (e.g., `ST_DWithin`).
- **Date Handling**: Store all timestamps as UTC.
- **Async Patterns**: Use `async`/`await` for all I/O operations.
