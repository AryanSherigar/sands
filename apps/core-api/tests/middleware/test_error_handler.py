"""Tests for global exception handlers."""

import pytest
from app.exceptions.base import BaseAppException
from app.main import app
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


async def test_custom_domain_exception_handled() -> None:
    """Verify BaseAppException returns domain error details."""

    @app.get("/test-domain-error")
    async def route_error():
        raise BaseAppException(
            message="Custom domain error", status_code=400, error_code="custom_code"
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/test-domain-error")
        assert response.status_code == 400
        assert response.json() == {
            "detail": "Custom domain error",
            "code": "custom_code",
        }


async def test_unhandled_exception_handled() -> None:
    """Verify unhandled Exception returns generic 500 error."""

    @app.get("/test-unhandled-error")
    async def route_unhandled():
        raise RuntimeError("Unexpected failure")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/test-unhandled-error")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
