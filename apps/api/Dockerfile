# Use the official uv image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory to the monorepo root
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && curl -sSf https://atlasgo.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# 1. Copy workspace metadata
# We MUST maintain the exact layout for uv to recognize the workspace members
COPY pyproject.toml uv.lock README.md ./
COPY packages/domain/pyproject.toml ./packages/domain/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml

# 2. Sync ALL workspace dependencies
# --all-packages ensures that fomo-api and domain dependencies are installed
# --no-install-project skips installing the actual code (which we haven't copied yet)
RUN uv sync --frozen --no-install-project --no-dev --all-packages

# 3. Copy the actual source code
COPY packages/__init__.py ./packages/__init__.py
COPY packages/domain ./packages/domain
COPY apps/api ./apps/api

# 4. Environment configuration
ENV PATH="/app/.venv/bin:$PATH"
# Force uv to use the workspace-root virtual environment
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
# Explicitly set PYTHONPATH to include /app for 'packages' imports
ENV PYTHONPATH="/app"

# 5. Runtime
WORKDIR /app

# Verify uvicorn is present in the synced environment
RUN uv run uvicorn --version

# Run uvicorn using 'uv run' to ensure the workspace environment is correctly activated.
# We run from the monorepo root so 'packages' is importable.
# We use --app-dir to add 'apps/api' to the PYTHONPATH so 'app' is importable.
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
