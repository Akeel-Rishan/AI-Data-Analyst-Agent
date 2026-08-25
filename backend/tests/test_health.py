"""Integration tests for health, root, and placeholder API routes."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous client connected directly to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client


async def test_health_basic(client: AsyncClient) -> None:
    """Verify the basic health endpoint reports a healthy application."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_health_db(client: AsyncClient) -> None:
    """Verify the database health endpoint can execute a query."""
    response = await client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"


async def test_health_full(client: AsyncClient) -> None:
    """Verify the full health endpoint includes every required check."""
    response = await client.get("/health/full")

    assert response.status_code == 200
    checks = response.json()["checks"]
    assert {"database", "upload_directory", "llm_configured"} <= checks.keys()


async def test_root(client: AsyncClient) -> None:
    """Verify the root endpoint advertises API documentation."""
    response = await client.get("/")

    assert response.status_code == 200
    assert "docs" in response.json()


async def test_dataset_endpoint(client: AsyncClient) -> None:
    """Verify the dataset listing endpoint responds successfully."""
    response = await client.get(
        "/api/datasets",
        headers={"X-Session-ID": "health-test-session"},
    )

    assert response.status_code == 200
    assert "datasets" in response.json()["data"]


async def test_404_unknown_route(client: AsyncClient) -> None:
    """Verify unknown routes retain FastAPI's standard 404 behavior."""
    response = await client.get("/unknown")

    assert response.status_code == 404
