"""Unit tests for trusted client-IP and user-key resolution."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.config import settings
from app.services.rate_limit.client_identity import (
    resolve_client_ip,
    resolve_user_id,
)
from starlette.requests import Request

SOCKET_PEER = "10.0.0.9"


def _request(headers: dict[str, str]) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
        "client": (SOCKET_PEER, 1234),
    }
    return Request(scope)


def _token(user_id: uuid.UUID, token_type: str = "access", **overrides) -> str:
    claims = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    } | overrides
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def test_zero_hops_uses_socket_peer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    request = _request({"X-Forwarded-For": "1.1.1.1"})

    assert resolve_client_ip(request) == SOCKET_PEER


def test_one_hop_takes_rightmost_entry(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    request = _request({"X-Forwarded-For": "6.6.6.6, 203.0.113.7"})

    assert resolve_client_ip(request) == "203.0.113.7"


def test_two_hops_ignores_spoofed_left_entries(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    request = _request({"X-Forwarded-For": "6.6.6.6, 203.0.113.7, 169.254.1.1"})

    assert resolve_client_ip(request) == "203.0.113.7"


def test_short_forwarded_chain_falls_back_to_peer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)

    assert resolve_client_ip(_request({"X-Forwarded-For": "1.1.1.1"})) == SOCKET_PEER


def test_x_real_ip_is_never_trusted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)

    assert resolve_client_ip(_request({"X-Real-IP": "1.2.3.4"})) == SOCKET_PEER


def test_valid_access_token_resolves_user() -> None:
    user_id = uuid.uuid4()
    request = _request({"Authorization": f"Bearer {_token(user_id)}"})

    assert resolve_user_id(request) == user_id


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        _token(uuid.uuid4(), token_type="refresh"),
        _token(uuid.uuid4(), exp=datetime.now(UTC) - timedelta(minutes=1)),
    ],
)
def test_invalid_tokens_resolve_to_anonymous(token: str) -> None:
    assert resolve_user_id(_request({"Authorization": f"Bearer {token}"})) is None


def test_dev_header_only_honoured_in_dev_environments(monkeypatch) -> None:
    user_id = uuid.uuid4()
    request = _request({"x-dev-user-id": str(user_id)})

    assert resolve_user_id(request) == user_id
    monkeypatch.setattr(settings, "environment", "production")
    assert resolve_user_id(request) is None
