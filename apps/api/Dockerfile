# ──────────────────────────── Stage 1: build ──────────────────────────────
# Resolve and compile all Python wheels into a workspace venv.
# gcc, libpq-dev are build-time only and never reach the runtime image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Build-time system deps only.  libpq-dev / gcc are needed when any wheel
# in the dependency tree requires compilation (e.g. psycopg2 non-binary).
# They are installed here so they cannot appear in the final image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy workspace metadata first so the dependency-install layer is cached
# independently of application source changes.
COPY pyproject.toml uv.lock README.md ./
COPY packages/domain/pyproject.toml ./packages/domain/pyproject.toml
COPY apps/api/pyproject.toml        ./apps/api/pyproject.toml

RUN uv sync --frozen --no-install-project --no-dev --all-packages

# Application source (after deps to preserve the dep-install cache layer).
COPY packages/__init__.py ./packages/__init__.py
COPY packages/domain      ./packages/domain
COPY apps/api             ./apps/api

# ─────────────────────────── Stage 2: runtime ─────────────────────────────
# Standard Python slim image — no compiler, no dev headers, no curl,
# no Atlas binary.  psycopg2-binary bundles its own libpq so no additional
# OS packages are required.
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Copy only the pre-built venv and application source from the builder.
# The build toolchain (gcc, libpq-dev, uv, apt caches) is left behind.
COPY --from=builder /app/.venv    /app/.venv
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/apps/api /app/apps/api

# Activate the pre-built venv.
# PYTHONPATH=/app makes `packages.*` absolute imports resolvable.
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Upgrade libgnutls30 to the patched Debian package that fixes CVE-2026-33845
# and CVE-2026-42010.  --only-upgrade ensures nothing new is installed if the
# package is already at the fixed version in a future base image rebuild.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade libgnutls30 \
    && rm -rf /var/lib/apt/lists/*

# Smoke-test: confirms the venv and all native extensions were copied correctly.
RUN uvicorn --version

# Non-root user with a fixed UID for predictable host-volume ownership.
RUN groupadd -r appgroup \
    && useradd -r -m -g appgroup -u 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Invoke uvicorn directly from the pre-built venv — no uv wrapper needed at
# runtime.  --app-dir adds apps/api to sys.path so `app` is importable
# alongside the `packages` namespace already on PYTHONPATH.
CMD ["uvicorn", "app.main:app", \
     "--app-dir", "apps/api", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
