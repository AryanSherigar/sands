import httpx
import pytest
from app.exceptions.alpha_exceptions import AlphaFeatureDisabledError, AlphaPausedError
from app.exceptions.base import BaseAppException
from app.middleware.error_handler import setup_error_handlers
from fastapi import FastAPI


@pytest.fixture
def client() -> httpx.AsyncClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/coded")
    async def coded() -> None:
        raise AlphaFeatureDisabledError()

    @app.get("/paused")
    async def paused() -> None:
        raise AlphaPausedError()

    @app.get("/uncoded")
    async def uncoded() -> None:
        raise BaseAppException("plain failure", status_code=409)

    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def test_exception_with_error_code_returns_code(client):
    response = await client.get("/coded")

    assert response.status_code == 403
    assert response.json() == {
        "detail": AlphaFeatureDisabledError().message,
        "code": "alpha_feature_disabled",
    }


async def test_exception_without_error_code_returns_detail_only(client):
    response = await client.get("/uncoded")

    assert response.status_code == 409
    assert response.json() == {"detail": "plain failure"}


async def test_paused_exception_maps_to_503_with_its_code(client):
    response = await client.get("/paused")

    assert response.status_code == 503
    assert response.json() == {
        "detail": AlphaPausedError().message,
        "code": "alpha_paused",
    }
