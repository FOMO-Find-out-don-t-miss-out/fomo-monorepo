import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(client: AsyncClient) -> None:
    """Test that /metrics endpoint is available."""
    response = await client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_returns_prometheus_text_format(client: AsyncClient) -> None:
    """Test that /metrics returns Prometheus text exposition format."""
    response = await client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]
    assert "# HELP" in response.text
    assert "# TYPE" in response.text


@pytest.mark.asyncio
async def test_metrics_contains_request_counter(client: AsyncClient) -> None:
    """Test that http_requests_total counter is present."""
    response = await client.get("/metrics")
    assert "http_requests_total" in response.text


@pytest.mark.asyncio
async def test_metrics_contains_latency_histogram(client: AsyncClient) -> None:
    """Test that http_request_duration_seconds histogram is present."""
    response = await client.get("/metrics")
    assert "http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_existing_api_routes_unaffected(client: AsyncClient) -> None:
    """Test that Prometheus middleware does not break existing routes."""
    # Health always returns 200 regardless of component status
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
