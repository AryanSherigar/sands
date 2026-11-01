"""IAM-mode service authentication: Google ID token, audience and caller allowlist."""

import time

import pytest
from app.config import Settings
from app.middleware import service_auth
from app.middleware.error_handler import setup_error_handlers
from app.middleware.service_auth import verify_service_identity
from app.routers.health import router as health_router
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

AUDIENCE = "https://memory.example.test"
TRS_CALLER = "trs@project.iam.gserviceaccount.com"
CORE_CALLER = "core@project.iam.gserviceaccount.com"
STRANGER = "stranger@elsewhere.iam.gserviceaccount.com"
GOOD_TOKEN = "good-token"
TOKEN_LIFETIME_SECONDS = 3600


def iam_settings(**overrides: object) -> Settings:
    fields: dict[str, object] = {
        "memory_auth_mode": "iam",
        "environment": "production",
        "memory_allowed_callers": f"{TRS_CALLER}, {CORE_CALLER}",
        "memory_iam_audience": AUDIENCE,
    }
    fields.update(overrides)
    return Settings(**fields)


class FakeVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.tokens: dict[str, dict[str, object]] = {
            GOOD_TOKEN: self.claims(TRS_CALLER),
            "stranger-token": self.claims(STRANGER),
            "unverified-token": {**self.claims(TRS_CALLER), "email_verified": False},
        }

    @staticmethod
    def claims(email: str) -> dict[str, object]:
        return {
            "email": email,
            "email_verified": True,
            "aud": AUDIENCE,
            "exp": time.time() + TOKEN_LIFETIME_SECONDS,
        }

    def __call__(self, token: str, audience: str) -> dict[str, object]:
        self.calls.append((token, audience))
        if audience != AUDIENCE or token not in self.tokens:
            raise ValueError("Token rejected")
        return self.tokens[token]


@pytest.fixture(autouse=True)
def clear_verified_cache() -> None:
    service_auth.clear_verified_claims()


@pytest.fixture
def verifier(monkeypatch: pytest.MonkeyPatch) -> FakeVerifier:
    fake = FakeVerifier()
    monkeypatch.setattr(service_auth, "verify_google_id_token", fake)
    monkeypatch.setattr(service_auth, "get_settings", iam_settings)
    return fake


@pytest.fixture
def client(verifier: FakeVerifier) -> TestClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/protected")
    async def protected(caller: str = Depends(verify_service_identity)) -> dict:
        return {"caller": caller}

    return TestClient(app)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_from_an_allowed_caller_is_accepted(client: TestClient) -> None:
    response = client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert response.status_code == 200
    assert response.json() == {"caller": TRS_CALLER}


def test_token_is_verified_against_the_configured_audience(
    client: TestClient, verifier: FakeVerifier
) -> None:
    client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert verifier.calls == [(GOOD_TOKEN, AUDIENCE)]


def test_missing_token_is_unauthenticated(client: TestClient) -> None:
    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_non_bearer_scheme_is_unauthenticated(client: TestClient) -> None:
    response = client.get("/protected", headers={"Authorization": "Basic abc"})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_token_the_verifier_rejects_is_invalid(client: TestClient) -> None:
    response = client.get("/protected", headers=bearer("forged"))

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_wrong_audience_is_invalid(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service_auth,
        "get_settings",
        lambda: iam_settings(memory_iam_audience="https://other.example.test"),
    )

    response = client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_unverified_email_is_invalid(client: TestClient) -> None:
    response = client.get("/protected", headers=bearer("unverified-token"))

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_caller_outside_the_allowlist_is_forbidden(client: TestClient) -> None:
    response = client.get("/protected", headers=bearer("stranger-token"))

    assert response.status_code == 403
    assert response.json()["code"] == "caller_not_allowed"


def test_verified_token_is_not_reverified_on_every_request(
    client: TestClient, verifier: FakeVerifier
) -> None:
    client.get("/protected", headers=bearer(GOOD_TOKEN))
    client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert len(verifier.calls) == 1


def test_cached_token_still_respects_a_changed_allowlist(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.get("/protected", headers=bearer(GOOD_TOKEN))
    monkeypatch.setattr(
        service_auth,
        "get_settings",
        lambda: iam_settings(memory_allowed_callers=CORE_CALLER),
    )

    response = client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert response.status_code == 403


def test_expired_cache_entry_is_verified_again(
    client: TestClient, verifier: FakeVerifier
) -> None:
    verifier.tokens[GOOD_TOKEN] = {
        **FakeVerifier.claims(TRS_CALLER),
        "exp": time.time() - 1,
    }
    client.get("/protected", headers=bearer(GOOD_TOKEN))
    client.get("/protected", headers=bearer(GOOD_TOKEN))

    assert len(verifier.calls) == 2


def test_dev_mode_is_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        service_auth,
        "get_settings",
        lambda: Settings(memory_auth_mode="dev", environment="development"),
    )
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/protected")
    async def protected(caller: str = Depends(verify_service_identity)) -> dict:
        return {"caller": caller}

    response = TestClient(app).get(
        "/protected", headers={"x-dev-service-name": "local-trs"}
    )

    assert response.json() == {"caller": "local-trs"}


def test_health_route_never_requires_a_token() -> None:
    assert health_router.dependencies == []
