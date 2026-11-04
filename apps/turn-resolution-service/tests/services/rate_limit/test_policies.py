"""Unit tests for TRS route-group burst policy matching."""

import pytest
from app.config import settings
from app.services.rate_limit.policies import (
    QuotaFeature,
    is_exempt_request,
    match_burst_policy,
    quota_policy,
)


@pytest.mark.parametrize(
    ("method", "path", "is_authenticated", "group"),
    [
        ("POST", "/v1/turn", True, "turn"),
        ("POST", "/v1/studio/assistant", True, "assistant"),
        ("POST", "/v1/voice/transcribe", True, "voice"),
        ("POST", "/v1/strategy/playthroughs/abc/art", True, "strategy_art"),
        ("GET", "/v1/session/abc/notifications", True, "read"),
        ("GET", "/v1/session/abc/spectate", False, "anonymous"),
        ("POST", "/v1/turn", False, "anonymous"),
    ],
)
def test_route_groups(
    method: str, path: str, is_authenticated: bool, group: str
) -> None:
    assert match_burst_policy(method, path, is_authenticated).group == group


def test_health_and_preflight_are_exempt() -> None:
    assert is_exempt_request("GET", "/health")
    assert is_exempt_request("OPTIONS", "/v1/turn")
    assert not is_exempt_request("POST", "/v1/turn")


def test_strategy_art_quota_uses_its_own_limits() -> None:
    policy = quota_policy(QuotaFeature.STRATEGY_ART)
    assert policy.feature == "strategy_art"
    assert policy.per_user_limit == settings.quota_strategy_art_per_user
    assert policy.global_limit == settings.quota_strategy_art_global


def test_strategy_dispatch_quota_is_separate_from_turns() -> None:
    policy = quota_policy(QuotaFeature.STRATEGY_DISPATCH)
    assert policy.feature == "strategy_dispatch"
    assert policy.per_user_limit == settings.quota_strategy_dispatch_per_user
    assert policy.global_limit == settings.quota_strategy_dispatch_global
    assert policy.feature != quota_policy(QuotaFeature.TURN).feature
