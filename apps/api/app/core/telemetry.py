import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBasedTraceIdRatio,
    Sampler,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Endpoints excluded from tracing to reduce cardinality and noise.
_EXCLUDED_URLS = "/api/v1/health,/metrics"


def setup_tracing(app: FastAPI) -> None:
    """Instrument the FastAPI app with OpenTelemetry tracing.

    Reads configuration from settings (OTEL_* env vars).
    If OTEL_ENABLED is False the function returns immediately so the app
    starts normally with no tracing overhead.
    OTel Collector and Jaeger backend are configured in fomo-platform.
    """
    if not settings.OTEL_ENABLED:
        return

    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})
    sampler = _build_sampler(settings.OTEL_TRACES_SAMPLER, settings.OTEL_TRACES_SAMPLER_ARG)
    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
            # BatchSpanProcessor is non-blocking; export failures won't crash the app.
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTel OTLP exporter configured: %s", settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        except Exception:
            logger.warning("Failed to configure OTel exporter; continuing without export", exc_info=True)  # noqa: E501

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls=_EXCLUDED_URLS)
    logger.info("OpenTelemetry tracing enabled (service=%s)", settings.OTEL_SERVICE_NAME)


def _build_sampler(name: str, ratio: float) -> Sampler:
    match name:
        case "parentbased_traceidratio":
            return ParentBasedTraceIdRatio(ratio)
        case "always_on":
            return ALWAYS_ON
        case "always_off":
            return ALWAYS_OFF
        case _:
            logger.warning(
                "Unknown OTEL_TRACES_SAMPLER %r, falling back to parentbased_traceidratio", name
            )
            return ParentBasedTraceIdRatio(ratio)
