import pytest
from app.middleware.error_handler import setup_error_handlers
from app.middleware.internal_auth import (
    HEADER_INTERNAL_SERVICE_TOKEN,
    require_internal_service_token,
)
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from tests.middleware.helpers import set_settings

SERVICE_TOKEN = "dev-internal-service-token-change-me"


def _client() -> TestClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/internal/ping", dependencies=[Depends(require_internal_service_token)])
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    return TestClient(app)


def _with_token(monkeypatch, token: str) -> TestClient:
    set_settings(monkeypatch, internal_service_token=token)
    return _client()


def test_correct_token_is_accepted(monkeypatch) -> None:
    client = _with_token(monkeypatch, SERVICE_TOKEN)
    response = client.get(
        "/internal/ping", headers={HEADER_INTERNAL_SERVICE_TOKEN: SERVICE_TOKEN}
    )
    assert response.status_code == 200


def test_wrong_token_is_rejected(monkeypatch) -> None:
    client = _with_token(monkeypatch, SERVICE_TOKEN)
    response = client.get(
        "/internal/ping", headers={HEADER_INTERNAL_SERVICE_TOKEN: "wrong"}
    )
    assert response.status_code == 401


def test_missing_header_is_rejected(monkeypatch) -> None:
    client = _with_token(monkeypatch, SERVICE_TOKEN)
    assert client.get("/internal/ping").status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {HEADER_INTERNAL_SERVICE_TOKEN: ""},
        {HEADER_INTERNAL_SERVICE_TOKEN: "anything"},
    ],
)
def test_unset_token_disables_the_endpoint(monkeypatch, headers) -> None:
    monkeypatch.delenv("INTERNAL_SERVICE_TOKEN", raising=False)
    set_settings(monkeypatch)
    response = _client().get("/internal/ping", headers=headers)
    assert response.status_code == 503
