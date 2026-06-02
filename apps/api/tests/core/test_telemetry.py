from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI


def test_setup_tracing_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns immediately with no OTel calls when OTEL_ENABLED is False."""
    from app.core import telemetry

    monkeypatch.setattr("app.core.telemetry.settings", MagicMock(OTEL_ENABLED=False))

    with patch("app.core.telemetry.FastAPIInstrumentor") as mock_inst:
        telemetry.setup_tracing(FastAPI())

    mock_inst.instrument_app.assert_not_called()


def test_setup_tracing_enabled_no_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """App starts without error when tracing is enabled but no endpoint is configured."""
    from app.core import telemetry

    monkeypatch.setattr(
        "app.core.telemetry.settings",
        MagicMock(
            OTEL_ENABLED=True,
            OTEL_SERVICE_NAME="fomo-api-test",
            OTEL_EXPORTER_OTLP_ENDPOINT=None,
            OTEL_TRACES_SAMPLER="parentbased_traceidratio",
            OTEL_TRACES_SAMPLER_ARG=0.1,
        ),
    )

    with (
        patch("app.core.telemetry.trace"),
        patch("app.core.telemetry.TracerProvider"),
        patch("app.core.telemetry.FastAPIInstrumentor") as mock_inst,
    ):
        app = FastAPI()
        telemetry.setup_tracing(app)

    mock_inst.instrument_app.assert_called_once_with(app, excluded_urls=telemetry._EXCLUDED_URLS)


def test_setup_tracing_enabled_with_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exporter and BatchSpanProcessor are wired when an endpoint is provided."""
    from app.core import telemetry

    monkeypatch.setattr(
        "app.core.telemetry.settings",
        MagicMock(
            OTEL_ENABLED=True,
            OTEL_SERVICE_NAME="fomo-api-test",
            OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4317",
            OTEL_TRACES_SAMPLER="parentbased_traceidratio",
            OTEL_TRACES_SAMPLER_ARG=0.1,
        ),
    )

    mock_provider = MagicMock()
    mock_exporter = MagicMock()
    mock_processor = MagicMock()

    with (
        patch("app.core.telemetry.trace"),
        patch("app.core.telemetry.TracerProvider", return_value=mock_provider),
        patch("app.core.telemetry.BatchSpanProcessor", return_value=mock_processor),
        patch(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter",
            return_value=mock_exporter,
        ),
        patch("app.core.telemetry.FastAPIInstrumentor"),
    ):
        telemetry.setup_tracing(FastAPI())

    mock_provider.add_span_processor.assert_called_once_with(mock_processor)


def test_tracing_disabled_by_default() -> None:
    """OTEL_ENABLED defaults to False — no secrets are required to start the app."""
    from app.core.config import Settings

    assert Settings.model_fields["OTEL_ENABLED"].default is False
    assert Settings.model_fields["OTEL_EXPORTER_OTLP_ENDPOINT"].default is None


def test_build_sampler_parentbased() -> None:
    from app.core.telemetry import _build_sampler
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

    sampler = _build_sampler("parentbased_traceidratio", 0.5)
    assert isinstance(sampler, ParentBasedTraceIdRatio)


def test_build_sampler_always_on() -> None:
    from app.core.telemetry import _build_sampler
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON

    assert _build_sampler("always_on", 1.0) is ALWAYS_ON


def test_build_sampler_always_off() -> None:
    from app.core.telemetry import _build_sampler
    from opentelemetry.sdk.trace.sampling import ALWAYS_OFF

    assert _build_sampler("always_off", 0.0) is ALWAYS_OFF


def test_build_sampler_unknown_falls_back_to_parentbased() -> None:
    from app.core.telemetry import _build_sampler
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

    sampler = _build_sampler("nonexistent_sampler", 0.2)
    assert isinstance(sampler, ParentBasedTraceIdRatio)
