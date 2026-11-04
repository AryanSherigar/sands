import httpx
import pytest
from app.exceptions.base import BaseAppException
from app.middleware.error_handler import setup_error_handlers
from fastapi import FastAPI


class CodedForbiddenError(BaseAppException):
    def __init__(self) -> None:
        super().__init__("Forbidden for a reason", status_code=403, error_code="coded")


class CodedUnavailableError(BaseAppException):
    def __init__(self) -> None:
        super().__init__("Try again later", status_code=503, error_code="unavailable")


@pytest.fixture
def client() -> httpx.AsyncClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/coded")
    async def coded() -> None:
        raise CodedForbiddenError()

    @app.get("/paused")
    async def paused() -> None:
        raise CodedUnavailableError()

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
        "detail": CodedForbiddenError().message,
        "code": "coded",
    }


async def test_exception_without_error_code_returns_detail_only(client):
    response = await client.get("/uncoded")

    assert response.status_code == 409
    assert response.json() == {"detail": "plain failure"}


async def test_unavailable_exception_maps_to_503_with_its_code(client):
    response = await client.get("/paused")

    assert response.status_code == 503
    assert response.json() == {
        "detail": CodedUnavailableError().message,
        "code": "unavailable",
    }
