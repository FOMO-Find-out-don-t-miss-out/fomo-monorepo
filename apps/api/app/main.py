import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import latency, requests

from app.api.api import api_router
from app.core.config import settings
from app.core.telemetry import setup_tracing

logging.basicConfig(level=logging.INFO, force=True)

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

setup_tracing(app)

# Set all origins enabled for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Prometheus metrics at /metrics.
# Handler labels use route templates (e.g. /api/v1/events/{event_id}) to avoid high cardinality.
# Kubernetes scraping, ServiceMonitor, and Grafana dashboards are handled in fomo-platform.
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics"],
).add(
    requests(),
    latency(),
).instrument(app).expose(app, include_in_schema=False)
