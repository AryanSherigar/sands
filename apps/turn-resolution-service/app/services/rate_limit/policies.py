"""Route-group burst policies and AI-feature quota policies for TRS."""

from dataclasses import dataclass
from enum import Enum

from app.config import settings

SECONDS_PER_DAY = 86400
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
EXEMPT_METHODS = frozenset({"OPTIONS", "HEAD"})
EXEMPT_PATHS = frozenset({"/health"})
EXEMPT_PATH_PREFIXES = ("/internal/",)


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
    TURN = "turn"
    SCENE_IMAGE = "scene_image"
    STRATEGY_ART = "strategy_art"
    TTS_NARRATION = "tts_narration"
    SPEECH_TO_TEXT = "speech_to_text"
    ASSISTANT = "assistant"


def _burst(group: str, limit: int, key_kind: KeyKind) -> BurstPolicy:
    return BurstPolicy(group, limit, settings.rate_limit_window_seconds, key_kind)


def ip_ceiling_policy() -> BurstPolicy:
    return _burst("ip_ceiling", settings.rate_limit_ip_ceiling_per_window, KeyKind.IP)


def is_exempt_path(path: str) -> bool:
    """Paths served without the proxy gate or burst limits: health checks and
    /internal/, which is reachable only on the backend network and is guarded
    by its own service token."""
    return path in EXEMPT_PATHS or path.startswith(EXEMPT_PATH_PREFIXES)


def is_exempt_request(method: str, path: str) -> bool:
    return method in EXEMPT_METHODS or is_exempt_path(path)


def _ai_policy(method: str, path: str) -> BurstPolicy | None:
    if method != "POST":
        return None
    if path == "/v1/turn":
        return _burst("turn", settings.rate_limit_turn_per_window, KeyKind.USER)
    if path == "/v1/studio/assistant":
        return _burst(
            "assistant", settings.rate_limit_assistant_per_window, KeyKind.USER
        )
    if path.startswith("/v1/playthroughs/") and path.endswith("/memory/retry"):
        return _burst(
            "memory_retry", settings.rate_limit_memory_retry_per_window, KeyKind.USER
        )
    if path.startswith("/v1/strategy/playthroughs/") and path.endswith("/art"):
        return _burst(
            "strategy_art", settings.rate_limit_strategy_art_per_window, KeyKind.USER
        )
    if path.startswith("/v1/scenes/") and path.endswith("/messages"):
        return _burst("scene", settings.rate_limit_scene_per_window, KeyKind.USER)
    if path.startswith("/v1/voice/"):
        return _burst("voice", settings.rate_limit_voice_per_window, KeyKind.USER)
    return None


def match_burst_policy(method: str, path: str, is_authenticated: bool) -> BurstPolicy:
    if not is_authenticated:
        return _burst("anonymous", settings.rate_limit_anonymous_per_window, KeyKind.IP)
    ai_policy = _ai_policy(method, path)
    if ai_policy is not None:
        return ai_policy
    if method in WRITE_METHODS:
        return _burst("write", settings.rate_limit_write_per_window, KeyKind.USER)
    return _burst("read", settings.rate_limit_read_per_window, KeyKind.USER)


def quota_policy(feature: QuotaFeature) -> QuotaPolicy:
    limits = {
        QuotaFeature.TURN: (settings.quota_turn_per_user, settings.quota_turn_global),
        QuotaFeature.SCENE_IMAGE: (
            settings.quota_scene_image_per_user,
            settings.quota_scene_image_global,
        ),
        QuotaFeature.STRATEGY_ART: (
            settings.quota_strategy_art_per_user,
            settings.quota_strategy_art_global,
        ),
        QuotaFeature.TTS_NARRATION: (
            settings.quota_tts_narration_per_user,
            settings.quota_tts_narration_global,
        ),
        QuotaFeature.SPEECH_TO_TEXT: (
            settings.quota_speech_to_text_per_user,
            settings.quota_speech_to_text_global,
        ),
        QuotaFeature.ASSISTANT: (
            settings.quota_assistant_per_user,
            settings.quota_assistant_global,
        ),
    }
    per_user_limit, global_limit = limits[feature]
    return QuotaPolicy(feature.value, per_user_limit, global_limit)
