"""Health check endpoint tests."""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health_check_returns_ok() -> None:
    """Verify /health endpoint returns HTTP 200 with ok status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
