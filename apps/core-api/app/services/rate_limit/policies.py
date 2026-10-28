"""Route-group burst policies and AI-feature quota policies for Core API."""

import re
from dataclasses import dataclass
from enum import Enum

from app.config import settings

SECONDS_PER_DAY = 86400
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
EXEMPT_METHODS = frozenset({"OPTIONS", "HEAD"})
EXEMPT_PATHS = frozenset({"/health"})
ALPHA_EVENTS_PATH = "/v1/alpha/events"
# NOTE: Local-disk media fallback only; in production media is served from
# GCS. Browsers fetch images without Authorization, so counting them would
# exhaust the anonymous per-IP budget on any image-heavy page.
EXEMPT_PATH_PREFIXES = ("/uploads/",)

_AI_GENERATION_PATTERNS = (
    re.compile(r"^/v1/uploads/generate-cover-image$"),
    re.compile(r"^/v1/scenarios/[^/]+/music/generate$"),
    re.compile(r"^/v1/scenarios/[^/]+/publish$"),
)
_UPLOAD_PATTERNS = (
    re.compile(r"^/v1/uploads/"),
    re.compile(r"^/v1/scenarios/[^/]+/music/[^/]+/upload$"),
)


class KeyKind(str, Enum):
    USER = "user"
    IP = "ip"
    USER_OR_IP = "user_or_ip"


@dataclass(frozen=True)
class BurstPolicy:
    group: str
    limit: int
    window_seconds: int
    key_kind: KeyKind


@dataclass(frozen=True)
class QuotaPolicy:
    feature: str
    per_user_limit: int
    global_limit: int
    window_seconds: int = SECONDS_PER_DAY


class QuotaFeature(str, Enum):
    COVER_IMAGE = "cover_image"
    MUSIC_GENERATION = "music_generation"
    PUBLISH = "publish"


def _burst(group: str, limit: int, key_kind: KeyKind) -> BurstPolicy:
    return BurstPolicy(group, limit, settings.rate_limit_window_seconds, key_kind)


def ip_ceiling_policy() -> BurstPolicy:
    return _burst("ip_ceiling", settings.rate_limit_ip_ceiling_per_window, KeyKind.IP)


def is_exempt_request(method: str, path: str) -> bool:
    if method in EXEMPT_METHODS or path in EXEMPT_PATHS:
        return True
    return path.startswith(EXEMPT_PATH_PREFIXES)


def _matches_any(path: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.match(path) for pattern in patterns)


def _authenticated_policy(method: str, path: str) -> BurstPolicy:
    if method == "POST" and _matches_any(path, _AI_GENERATION_PATTERNS):
        return _burst(
            "ai_generation", settings.rate_limit_ai_generation_per_window, KeyKind.USER
        )
    if method == "POST" and _matches_any(path, _UPLOAD_PATTERNS):
        return _burst("upload", settings.rate_limit_upload_per_window, KeyKind.USER)
    if method in WRITE_METHODS:
        return _burst("write", settings.rate_limit_write_per_window, KeyKind.USER)
    return _burst("read", settings.rate_limit_read_per_window, KeyKind.USER)


def match_burst_policy(method: str, path: str, is_authenticated: bool) -> BurstPolicy:
    if path.startswith("/v1/auth/"):
        return _burst("auth", settings.rate_limit_auth_per_window, KeyKind.IP)
    if path == "/v1/logs":
        return _burst("logs", settings.rate_limit_logs_per_window, KeyKind.USER_OR_IP)
    if not is_authenticated:
        return _burst("anonymous", settings.rate_limit_anonymous_per_window, KeyKind.IP)
    if path == ALPHA_EVENTS_PATH:
        return _burst(
            "alpha_events", settings.rate_limit_alpha_events_per_window, KeyKind.USER
        )
    return _authenticated_policy(method, path)


def quota_policy(feature: QuotaFeature) -> QuotaPolicy:
    limits = {
        QuotaFeature.COVER_IMAGE: (
            settings.quota_cover_image_per_user,
            settings.quota_cover_image_global,
        ),
        QuotaFeature.MUSIC_GENERATION: (
            settings.quota_music_generation_per_user,
            settings.quota_music_generation_global,
        ),
        QuotaFeature.PUBLISH: (
            settings.quota_publish_per_user,
            settings.quota_publish_global,
        ),
    }
    per_user_limit, global_limit = limits[feature]
    return QuotaPolicy(feature.value, per_user_limit, global_limit)
