import pytest
from app.exceptions.base import SimulationServiceError
from app.middleware.error_handler import setup_error_handlers
from fastapi import FastAPI
from fastapi.testclient import TestClient

HTTP_CONFLICT = 409


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/domain")
    def raise_domain_error() -> None:
        raise SimulationServiceError("nope", status_code=HTTP_CONFLICT, code="conflict")

    @app.get("/boom")
    def raise_unexpected_error() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_domain_error_maps_to_its_status_and_code(client: TestClient) -> None:
    response = client.get("/domain")
    assert response.status_code == HTTP_CONFLICT
    assert response.json() == {"detail": "nope", "code": "conflict"}


def test_unexpected_error_is_a_generic_500(client: TestClient) -> None:
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
