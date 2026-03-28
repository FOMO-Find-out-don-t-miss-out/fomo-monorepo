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
│   ├── api-spec/              # TypeSpec API Definitions (Source of Truth)
│   └── domain/                # Shared Logic & Domain Models (SQLModel, Services)
├── infra/                     # Docker & Database Provisioning
├── tooling/                   # Quality & Build Scripts
├── docker-compose.yml         # Local Infrastructure Orchestration
├── pyproject.toml             # UV Workspace Configuration
├── ruff.toml                  # Strict 2026 Quality Standards
└── CORE_RULES.md              # Mandatory Developer Guidelines
```

---

## 📜 API Contracts
We use [TypeSpec](https://typespec.io/) to define our API contract as the single source of truth.
- **Location**: `packages/api-spec/main.tsp`
- **Build Spec**:
  ```bash
  cd packages/api-spec
  npm install
  tsp compile main.tsp
  ```
- **Goal**: Generate OpenAPI/FastAPI/TypeScript models from this spec to ensure consistency.

---

## 🏗 Development Rules
To ensure consistent quality and maintainability, all contributors must strictly adhere to our project guidelines:
- [CORE_RULES.md](./CORE_RULES.md) - **Mandatory Architectural and Quality Standards.**

---

## ✅ Quality Gates
We enforce strict industry standards for every contribution:
- **Linting**: No warnings allowed (Ruff).
- **Type Safety**: Mandatory type hints for all public functions (ANN).
- **Security**: Automated security scanning (S).
- **Coverage**: Minimum **95% code coverage** is enforced.

To run the full quality suite locally:
```bash
./tooling/check-quality.sh
```

---

## 🚀 Getting Started (First-Time Setup)

Follow these steps exactly to initialize the project after cloning.

### 1. Prerequisites
Ensure you have the following installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/)
- [uv](https://github.com/astral-sh/uv) (Recommended for Python dependency management)

### 2. Python Dependency Management
We use [uv](https://github.com/astral-sh/uv) to manage Python dependencies across the monorepo. To sync all dependencies:
```bash
uv sync
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fomo
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/fomo
MAPBOX_ACCESS_TOKEN=your_mapbox_token
GOOGLE_API_KEY=your_gemini_api_key
N8N_WEBHOOK_URL=http://fomo_harvester_n8n:5678/webhook/your-id
```

### 4. Spin up the Infrastructure
This will build the API, Dashboard, and start PostgreSQL (PostGIS), Redis, and n8n.
```bash
docker compose up -d --build
```

### 5. Initialize the Database Schema
Since the database starts empty, you must apply the Alembic migrations to create the tables:
```bash
docker compose exec api alembic upgrade head
```

### 6. Verify the Installation
- **Moderation Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **n8n Dashboard**: [http://localhost:5678](http://localhost:5678)
- **PostgreSQL**: Accessible at `localhost:5432` from your host machine.

---

## 🛠 Tooling

### MCP Awareness (Infrastructure Bridge)
To improve AI-driven development, this monorepo supports the **Model Context Protocol (MCP)**.
- **Config**: `infra/mcp-config.json`
- **Purpose**: Allows AI agents to connect directly to the live PostgreSQL/PostGIS database to inspect schemas, indexes, and constraints.
- **Benefit**: Eliminates hallucinations when proposing database migrations or SQLModel changes. Agents can verify the state of the infrastructure in real-time.

---

## 🛠 Development Workflows

### Database Migrations
When you modify models in `packages/domain/`:
1. **Generate a migration**:
   ```bash
   docker compose exec api alembic revision --autogenerate -m "describe_your_change"
   ```
2. **Apply the migration**:
   ```bash
   docker compose exec api alembic upgrade head
   ```

#### Resolving "Schema Drift" Errors
If the quality gates fail with "CRITICAL: Schema Drift Detected", it means your SQLModel definitions do not match the live database schema.
- **Why it happens**: You modified a model but didn't create/apply a migration, or your local DB is out of sync.
- **Solution**: 
  1. Ensure your local database is running: `docker compose up -d db`.
  2. Generate a new migration: `docker compose exec api alembic revision --autogenerate -m "fix_drift"`.
  3. Apply it: `docker compose exec api alembic upgrade head`.
  4. Re-run the quality check: `./tooling/check-quality.sh`.

### Running Scrapers
You can trigger the internal scraper manually via the API:
```bash
# via Curl
curl -X POST http://localhost:8000/api/v1/internal/run-scraper
```
*Note: This runs in the background and will ingest data into the `pending_events` table.*

---

## 🛠 Troubleshooting

### Installing `uv` on Windows
If `uv` is not found, install it locally via the official PowerShell script:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Docker Build Context & Monorepo Integrity
In this monorepo, **all Docker builds must be executed from the root directory**. This is because services in `apps/` depend on shared packages in `packages/` (e.g., the API depends on the `domain` package).

If you build from inside `apps/api/`, Docker will not be able to "see" the `packages/` directory, and the build will fail. Our `docker-compose.yml` is already configured to handle this correctly.

If building manually:
```bash
# CORRECT: Run from monorepo root
docker build -t fomo-api -f apps/api/Dockerfile .

# INCORRECT: Will fail to find packages/domain
cd apps/api && docker build -t fomo-api .
```

---

## 🛠 Troubleshooting
...
### Build Failures
**Important**: Ensure your Docker build context is at the **monorepo root**. Shared logic in `packages/` is invisible to Docker if the context is set to a subdirectory.

---

## 🔒 Security Note
Never commit your `.env` file. A `.gitignore` is included to protect your credentials.
