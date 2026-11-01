"""Router-level tests for GET /health, using dependency overrides. No real DB."""

from app.main import create_app
from app.models.health import HealthExtensions, HealthResponse
from app.services.health_service import get_health_service
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class _StubHealthService:
    def __init__(self, response: HealthResponse) -> None:
        self._response = response

    async def check_health(self) -> HealthResponse:
        return self._response


def _override_health_service(app: FastAPI, response: HealthResponse) -> None:
    app.dependency_overrides[get_health_service] = lambda: _StubHealthService(response)


async def test_health_ok_returns_200() -> None:
    app = create_app()
    response = HealthResponse(
        status="ok",
        database=True,
        extensions=HealthExtensions(vector=True, pg_textsearch=True),
    )
    _override_health_service(app, response)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        result = await client.get("/health")

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["extensions"] == {"vector": True, "pg_textsearch": True}
    app.dependency_overrides.clear()


async def test_health_unreachable_database_returns_503() -> None:
    app = create_app()
    response = HealthResponse(
        status="error",
        database=False,
        extensions=HealthExtensions(vector=False, pg_textsearch=False),
    )
    _override_health_service(app, response)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        result = await client.get("/health")

    assert result.status_code == 503
    body = result.json()
    assert body["status"] == "error"
    assert body["database"] is False
    app.dependency_overrides.clear()
