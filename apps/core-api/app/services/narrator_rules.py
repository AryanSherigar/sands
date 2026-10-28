"""Scenario-authored narrator settings kept in `rules` and pinned into the
playthrough snapshot for TRS: an output cap and the intent-marker group."""

import re

import structlog

logger = structlog.get_logger()

RULES_KEY_NARRATION_MAX_OUTPUT_TOKENS = "narration_max_output_tokens"
SNAPSHOT_KEY_NARRATION_MAX_OUTPUT_TOKENS = "narration_max_output_tokens"
MIN_NARRATION_OUTPUT_TOKENS = 200
MAX_NARRATION_OUTPUT_TOKENS = 4096
EVENT_NARRATION_LIMIT_IGNORED = "narration_limit_ignored"

RULES_KEY_INTENT_MARKER_GROUP = "intent_marker_group"
SNAPSHOT_KEY_INTENT_MARKER_GROUP = "intent_marker_group"
EVENT_INTENT_MARKER_GROUP_IGNORED = "intent_marker_group_ignored"
_GROUP_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def narration_limit_from_rules(rules: dict[str, object]) -> int | None:
    """None keeps the provider default; an out-of-range or non-integer value is
    logged and ignored rather than failing playthrough creation."""
    value = rules.get(RULES_KEY_NARRATION_MAX_OUTPUT_TOKENS)
    if value is None:
        return None
    is_valid = (
        isinstance(value, int)
        and not isinstance(value, bool)
        and MIN_NARRATION_OUTPUT_TOKENS <= value <= MAX_NARRATION_OUTPUT_TOKENS
    )
    if not is_valid:
        logger.warning(EVENT_NARRATION_LIMIT_IGNORED, value=repr(value))
        return None
    return int(value)


def intent_marker_group_from_rules(
    rules: dict[str, object], state_schema: dict[str, object]
) -> str | None:
    """The state-schema group whose fields the narrator may set with an intent
    marker, or None. A name that is not an object group in the schema is logged
    and ignored, so a typo cannot silently point the marker at nothing."""
    value = rules.get(RULES_KEY_INTENT_MARKER_GROUP)
    if value is None:
        return None
    definition = state_schema.get(value) if isinstance(value, str) else None
    is_group = (
        isinstance(value, str)
        and _GROUP_NAME.match(value) is not None
        and isinstance(definition, dict)
        and definition.get("type") == "object"
    )
    if not is_group:
        logger.warning(EVENT_INTENT_MARKER_GROUP_IGNORED, value=repr(value))
        return None
    return str(value)
