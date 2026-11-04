"""Unit tests for route-group burst policy matching."""

import pytest
from app.services.rate_limit.policies import (
    KeyKind,
    is_exempt_request,
    match_burst_policy,
)


@pytest.mark.parametrize(
    ("method", "path", "is_authenticated", "group"),
    [
        ("POST", "/v1/auth/token", False, "auth"),
        ("POST", "/v1/auth/refresh", True, "auth"),
        ("POST", "/v1/logs", False, "logs"),
        ("GET", "/v1/scenarios", False, "anonymous"),
        ("POST", "/v1/uploads/generate-cover-image", True, "ai_generation"),
        ("POST", "/v1/scenarios/abc/publish", True, "ai_generation"),
        ("POST", "/v1/uploads/avatar", True, "upload"),
        ("POST", "/v1/scenarios/abc/music/combat/upload", True, "upload"),
        ("PATCH", "/v1/scenarios/abc", True, "write"),
        ("DELETE", "/v1/users/me", True, "write"),
        ("GET", "/v1/users/me", True, "read"),
    ],
)
def test_route_groups(
    method: str, path: str, is_authenticated: bool, group: str
) -> None:
    assert match_burst_policy(method, path, is_authenticated).group == group


def test_auth_group_is_always_keyed_by_ip() -> None:
    assert match_burst_policy("POST", "/v1/auth/token", True).key_kind == KeyKind.IP


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/health"), ("OPTIONS", "/v1/scenarios"), ("GET", "/uploads/a.png")],
)
def test_exempt_requests(method: str, path: str) -> None:
    assert is_exempt_request(method, path)


def test_api_requests_are_not_exempt() -> None:
    assert not is_exempt_request("GET", "/v1/scenarios")


@pytest.mark.parametrize("suffix", ["generate-regions", "generate-art"])
def test_map_generation_paths_use_the_ai_generation_group(suffix: str) -> None:
    generation = match_burst_policy(
        "POST", "/v1/uploads/generate-cover-image", is_authenticated=True
    )
    policy = match_burst_policy(
        "POST", f"/v1/scenarios/abc/strategy-map/{suffix}", is_authenticated=True
    )

    assert policy.group == generation.group
