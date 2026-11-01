import pytest
from fastapi.testclient import TestClient

from tests.middleware.helpers import (
    OTHER_SECRET,
    TEST_SECRET,
    USER_ID,
    make_auth_app,
    make_token,
    set_settings,
    unsigned_token,
)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    set_settings(monkeypatch, secret_key=TEST_SECRET)
    return TestClient(make_auth_app())


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_access_token_authenticates(client) -> None:
    response = client.get("/me", headers=_bearer(make_token()))
    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID}


@pytest.mark.parametrize("claim_type", ["refresh", None])
def test_only_access_tokens_are_accepted(client, claim_type) -> None:
    response = client.get("/me", headers=_bearer(make_token(type=claim_type)))
    assert response.status_code == 401


def test_expired_token_is_rejected(client) -> None:
    assert client.get("/me", headers=_bearer(make_token(exp=1))).status_code == 401


def test_token_without_expiry_is_rejected(client) -> None:
    assert client.get("/me", headers=_bearer(make_token(exp=None))).status_code == 401


def test_token_signed_with_another_secret_is_rejected(client) -> None:
    token = make_token(secret=OTHER_SECRET)
    assert client.get("/me", headers=_bearer(token)).status_code == 401


def test_token_signed_with_another_algorithm_is_rejected(client) -> None:
    token = make_token(algorithm="HS512")
    assert client.get("/me", headers=_bearer(token)).status_code == 401


def test_unsigned_token_is_rejected(client) -> None:
    response = client.get("/me", headers=_bearer(unsigned_token()))
    assert response.status_code == 401


def test_subject_must_be_a_uuid(client) -> None:
    token = make_token(sub="not-a-uuid")
    assert client.get("/me", headers=_bearer(token)).status_code == 401


def test_missing_credentials_are_rejected(client) -> None:
    assert client.get("/me").status_code == 401


def test_dev_header_authenticates_in_development(client) -> None:
    response = client.get("/me", headers={"x-dev-user-id": USER_ID})
    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID}


def test_invalid_dev_header_is_rejected(client) -> None:
    assert client.get("/me", headers={"x-dev-user-id": "nope"}).status_code == 401


def test_dev_header_is_ignored_in_production(monkeypatch) -> None:
    set_settings(monkeypatch, environment="production", secret_key=TEST_SECRET)
    client = TestClient(make_auth_app())
    assert client.get("/me", headers={"x-dev-user-id": USER_ID}).status_code == 401
    assert client.get("/me", headers=_bearer(make_token())).status_code == 200
