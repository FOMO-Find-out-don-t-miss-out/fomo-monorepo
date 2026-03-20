# FOMO Monorepo

Welcome to the **FOMO** (Fear Of Missing Out) monorepo. This project is a highly scalable, real-time event discovery platform that combines automated web harvesting, human-in-the-loop moderation, and a high-performance FastAPI backend with spatial (PostGIS) capabilities.

## 🏗 Architecture Overview

The project is structured as a modular monorepo:

- **`services/api`**: FastAPI backend using SQLModel (SQLAlchemy 2.0 + Pydantic).
- **`services/harvester`**: Python-based scrapers for automated data collection.
- **`infra/`**: Docker and database provisioning scripts.
- **`apps/mobile`**: Expo/React Native mobile application (Initial structure).
- **`n8n`**: Integrated workflow automation for the harvester pipeline.

---

## 🚀 Getting Started (First-Time Setup)

Follow these steps exactly to initialize the project after cloning.

### 1. Prerequisites
Ensure you have the following installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fomo
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/fomo
N8N_WEBHOOK_URL=http://fomo_harvester_n8n:5678/webhook/your-id
```

### 3. Spin up the Infrastructure
This will build the API image and start PostgreSQL (PostGIS), Redis, and n8n.
```bash
docker compose up -d --build
```

### 4. Initialize the Database Schema
Since the database starts empty, you must apply the Alembic migrations to create the tables:
```bash
docker compose exec api alembic upgrade head
```

### 5. Verify the Installation
- **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **n8n Dashboard**: [http://localhost:5678](http://localhost:5678)
- **PostgreSQL**: Accessible at `localhost:5432` from your host machine.

---

## 🛠 Development Workflows

### Database Migrations
When you modify models in `app/models/`:
1. **Generate a migration**:
   ```bash
   docker compose exec api alembic revision --autogenerate -m "describe_your_change"
   ```
2. **Apply the migration**:
   ```bash
   docker compose exec api alembic upgrade head
   ```

### Running Scrapers
You can trigger the internal scraper manually via the API:
```bash
# via Curl
curl -X POST http://localhost:8000/api/v1/internal/run-scraper
```
*Note: This runs in the background and will ingest data into the `pending_events` table.*

### Moderation Queue
New events arrive in `pending_events`. To move them to the live `events` table:
1. Find the `pending_id` from the database.
2. Call the approval endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/internal/approve/{pending_id}
   ```

---

## 🧪 Testing & Quality Assurance

The project maintains high standards with **Ruff** for linting and **Pytest** for comprehensive testing, targeting **95-96%+ code coverage**.

### 1. Running Linting
We use Ruff for extremely fast Python linting and formatting checks:
```bash
docker compose exec api ruff check .
```

### 2. Running Tests
All API unit and integration tests can be executed within the container:
```bash
docker compose exec api pytest
```

### 3. Monitoring Test Coverage
To check the current code coverage and identify untested lines, run:
```bash
docker compose exec api pytest --cov=app --cov-report=term-missing
```

The project is configured via `.coveragerc` to:
- **Fail** if total coverage drops below **95%**.
- **Exclude** migrations and boilerplate from the report.
- **Show** exact line numbers that are missing coverage.

### 4. Local Testing (Optional)
If you have a local Python environment (3.12+) and want to run tests without Docker:
1. **Install dependencies**: `pip install -r services/api/requirements.txt`
2. **Run tests**: `python -m pytest --cov=app --cov-report=term-missing` from the `services/api` directory.
   *Note: Local tests use an in-memory SQLite database with PostGIS mocks for speed and portability.*

---

## 🔒 Security Note
Never commit your `.env` file. A `.gitignore` is included to protect your credentials.
