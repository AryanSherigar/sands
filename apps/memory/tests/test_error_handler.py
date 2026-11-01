"""Tests for error handler code field."""

from uuid import uuid4

import pytest
from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.middleware.error_handler import setup_error_handlers
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_handlers() -> FastAPI:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/test-error")
    def raise_playthrough_not_registered() -> None:
        playthrough_id = uuid4()
        raise PlaythroughNotRegisteredError(playthrough_id)

    return app


def test_error_response_includes_code_field(
    app_with_handlers: FastAPI,
) -> None:
    client = TestClient(app_with_handlers)
    response = client.get("/test-error")

    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert data["code"] == "not_registered"
