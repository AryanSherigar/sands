"""Builds the public face of a rule check from its snapshot definition.

Shared by the trigger step (which stamps it) and the resolver (which needs the
recall variant ids). Results, mutations, timeout outcomes and the correct recall
index never appear here (docs/specs/rules-horror-engine/rule-checks-tool.spec.md
§2.4).
"""

import random

from app.config import settings
from app.models.check_event import (
    RuleCheckEventPayload,
    RuleCheckOption,
    RuleCheckVariant,
)
from app.turn import time_entry

KIND_RECALL = "recall"
KIND_TIME_ENTRY = "time_entry"
ENTRY_OPTION_ID = "enter"
REJECT_OPTION_ID = "reject"
DEFAULT_ENTER_LABEL = "Write it in the Log"
DEFAULT_REJECT_LABEL = "Reject the visitor"
VARIANT_ID_PREFIX = "v"


def variant_id_for(index: int) -> str:
    return f"{VARIANT_ID_PREFIX}{index}"


def parse_variant_index(variant_id: str) -> int | None:
    suffix = variant_id.removeprefix(VARIANT_ID_PREFIX)
    if suffix == variant_id or not suffix.isdigit():
        return None
    return int(suffix)


def build_event_payload(
    definition: dict[str, object],
    *,
    check_id: str,
    now_ms: int,
    reopen_count: int,
    state: dict[str, object] | None = None,
) -> RuleCheckEventPayload:
    raw_params = definition.get("params")
    params = raw_params if isinstance(raw_params, dict) else {}
    return RuleCheckEventPayload(
        **_time_entry_fields(definition, params, state or {}),
        check_id=check_id,
        kind=str(definition.get("kind")),
        prompt=str(params.get("prompt", "")),
        options=_options_for(definition, params),
        variants=_shuffled_variants(params, check_id),
        window_ms=_window_ms_of(params),
        issued_at=now_ms,
        hidden_grace_ms=settings.rule_check_hidden_grace_ms,
        reopen_count=reopen_count,
    )


def _time_entry_fields(
    definition: dict[str, object], params: dict[str, object], state: dict[str, object]
) -> dict[str, object]:
    if definition.get("kind") != KIND_TIME_ENTRY:
        return {}
    wall_minute = time_entry.wall_minute_of_day(params, state)
    told_minute = params.get("told_minute_of_day")
    return {
        "told_label": _label_of(told_minute),
        "wall_label": _label_of(wall_minute),
        "wall_minute_of_day": wall_minute,
    }


def _label_of(minute: object) -> str | None:
    if isinstance(minute, bool) or not isinstance(minute, int):
        return None
    return time_entry.format_minute_of_day(minute)


def _time_entry_options(params: dict[str, object]) -> list[RuleCheckOption]:
    return [
        RuleCheckOption(
            id=ENTRY_OPTION_ID,
            label=str(params.get("enter_label") or DEFAULT_ENTER_LABEL),
        ),
        RuleCheckOption(
            id=REJECT_OPTION_ID,
            label=str(params.get("reject_label") or DEFAULT_REJECT_LABEL),
        ),
    ]


def _options_for(
    definition: dict[str, object], params: dict[str, object]
) -> list[RuleCheckOption]:
    if definition.get("kind") == KIND_TIME_ENTRY:
        return _time_entry_options(params)
    return _public_options(params)


def _public_options(params: dict[str, object]) -> list[RuleCheckOption]:
    options = params.get("options")
    if not isinstance(options, list):
        return []
    return [
        RuleCheckOption(id=str(option["id"]), label=str(option["label"]))
        for option in options
        if isinstance(option, dict)
    ]


def _shuffled_variants(
    params: dict[str, object], check_id: str
) -> list[RuleCheckVariant]:
    texts = params.get("variants")
    if not isinstance(texts, list):
        return []
    variants = [
        RuleCheckVariant(id=variant_id_for(index), text=str(text))
        for index, text in enumerate(texts)
    ]
    random.Random(check_id).shuffle(variants)
    return variants


def _window_ms_of(params: dict[str, object]) -> int:
    window = params.get("window_ms")
    return window if isinstance(window, int) else 0
