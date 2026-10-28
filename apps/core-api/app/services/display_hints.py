"""Validate and strip `display` hints on state_schema fields (tool `status_hud`).

A hint tells the play screen how to show a state field: a clock, a meter or a
tier. It is plain JSON inside the existing state_schema column.
"""

import copy
import re
from collections.abc import Iterator, Sequence
from itertools import pairwise

from app.db.models.scenario_music import MOOD_SLOTS
from app.exceptions.display_hint_exceptions import DisplayHintValidationError
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.services.state_schema_paths import enum_option_values, field_at_path

STATUS_HUD_TOOL_KEY = "status_hud"
HINT_KINDS = ("clock", "meter", "tier")
CLOCK_FORMATS = ("12h", "24h")
_TIME_OF_DAY = re.compile(r"^(?P<hour>\d{2}):(?P<minute>\d{2})$")
_TRACK_OBJECT_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)*\.mp3$")
MAX_HOUR = 23
MAX_MINUTE = 59
MAX_INTRUSIVE_THOUGHTS = 8
MAX_INTRUSIVE_THOUGHT_LENGTH = 60
EFFECT_THRESHOLD_KEYS = ("moderate_below", "critical_below", "intrusive_below")


def validate_display_hints(
    state_schema: dict[str, object],
    enabled_tools: Sequence[str],
    previous_schema: dict[str, object] | None = None,
) -> None:
    """With the tool on, every hint is validated. With it off, only a hint that
    is new or changed is refused: hints left over from when the tool was on stay
    inert and must not block unrelated schema edits."""
    hinted = list(_hinted_fields(state_schema))
    if not hinted:
        return
    if STATUS_HUD_TOOL_KEY not in enabled_tools:
        _ensure_hints_are_unchanged(hinted, previous_schema or {})
        return
    for path, field in hinted:
        _validate_one_hint(path, field, state_schema)
    _validate_hint_counts(hinted)


def _ensure_hints_are_unchanged(
    hinted: list[tuple[str, dict[str, object]]], previous_schema: dict[str, object]
) -> None:
    for path, field in hinted:
        previous = field_at_path(previous_schema, path)
        if previous is None or previous.get("display") != field["display"]:
            raise ToolNotEnabledError(STATUS_HUD_TOOL_KEY)


def count_display_hints(state_schema: dict[str, object]) -> int:
    return sum(1 for _ in _hinted_fields(state_schema))


def strip_display_hints(state_schema: dict[str, object]) -> dict[str, object]:
    return {name: _without_hint(field) for name, field in state_schema.items()}


def _without_hint(field: object) -> object:
    if not isinstance(field, dict):
        return copy.deepcopy(field)
    stripped = {k: copy.deepcopy(v) for k, v in field.items() if k != "display"}
    nested = field.get("fields")
    if isinstance(nested, dict):
        stripped["fields"] = strip_display_hints(nested)
    return stripped


def _hinted_fields(
    fields: dict[str, object], prefix: str = ""
) -> Iterator[tuple[str, dict[str, object]]]:
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        path = f"{prefix}{name}"
        if "display" in field:
            yield path, field
        nested = field.get("fields")
        if isinstance(nested, dict):
            yield from _hinted_fields(nested, f"{path}.")


def _fail(path: str, reason: str) -> DisplayHintValidationError:
    return DisplayHintValidationError(f"Display hint on '{path}': {reason}")


def _validate_one_hint(
    path: str, field: dict[str, object], state_schema: dict[str, object]
) -> None:
    hint = field["display"]
    if not isinstance(hint, dict) or hint.get("kind") not in HINT_KINDS:
        raise _fail(path, f"kind must be one of {', '.join(HINT_KINDS)}")
    if field.get("hidden") is True:
        raise _fail(path, "a hidden field cannot be displayed")
    kind = hint["kind"]
    if kind == "tier":
        _validate_tier(path, field, hint)
        return
    if field.get("type") != "number":
        raise _fail(path, f"a {kind} needs a number field")
    if kind == "clock":
        _validate_clock(path, hint, state_schema)
    else:
        _validate_meter(path, hint)


def _validate_tier(
    path: str, field: dict[str, object], hint: dict[str, object]
) -> None:
    if field.get("type") != "enum":
        raise _fail(path, "a tier needs an enum field")
    mood_map = hint.get("mood_map")
    track_map = hint.get("track_map")
    if mood_map is None and track_map is None:
        return
    options = enum_option_values(field.get("options"))
    if mood_map is not None:
        _validate_mood_map(path, options, mood_map)
    if track_map is not None:
        _validate_track_map(path, options, track_map)


def _validate_mood_map(path: str, options: list[str], mood_map: object) -> None:
    if not isinstance(mood_map, dict):
        raise _fail(path, "mood_map must be an object")
    for option, mood in mood_map.items():
        if option not in options:
            raise _fail(path, f"mood_map key '{option}' is not an enum option")
        if mood not in MOOD_SLOTS:
            raise _fail(path, f"mood '{mood}' is not a known mood")


def _validate_track_map(path: str, options: list[str], track_map: object) -> None:
    if not isinstance(track_map, dict):
        raise _fail(path, "track_map must be an object")
    for option, object_key in track_map.items():
        if option not in options:
            raise _fail(path, f"track_map key '{option}' is not an enum option")
        if not isinstance(object_key, str) or not _TRACK_OBJECT_KEY.match(object_key):
            raise _fail(path, f"track_map value for '{option}' is not a valid mp3 key")


def tier_track_keys(state_schema: dict[str, object]) -> dict[str, str]:
    """Object keys of the tier tracks, empty when no tier hint declares any."""
    for _, field in _hinted_fields(state_schema):
        hint = field["display"]
        if not isinstance(hint, dict) or hint.get("kind") != "tier":
            continue
        track_map = hint.get("track_map")
        if isinstance(track_map, dict):
            return {str(tier): str(key) for tier, key in track_map.items()}
    return {}


def _validate_clock(
    path: str, hint: dict[str, object], state_schema: dict[str, object]
) -> None:
    _validate_start_time(path, hint.get("start"))
    if hint.get("format", "12h") not in CLOCK_FORMATS:
        raise _fail(path, "format must be 12h or 24h")
    glitch = hint.get("glitch")
    if glitch is None:
        return
    source = glitch.get("source") if isinstance(glitch, dict) else None
    source_field = field_at_path(state_schema, str(source)) if source else None
    source_hint = source_field.get("display") if source_field else None
    if not isinstance(source_hint, dict) or source_hint.get("kind") != "meter":
        raise _fail(path, "glitch source must be a declared meter field")
    _validate_glitch_numbers(path, glitch)


def _validate_glitch_numbers(path: str, glitch: dict[str, object]) -> None:
    if "below" in glitch and not _is_number(glitch["below"]):
        raise _fail(path, "glitch below must be a number")
    chance = glitch.get("chance")
    if chance is not None and not (_is_number(chance) and 0 <= chance <= 1):  # type: ignore[operator]
        raise _fail(path, "glitch chance must be a number from 0 to 1")


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _validate_start_time(path: str, start: object) -> None:
    match = _TIME_OF_DAY.match(start) if isinstance(start, str) else None
    if (
        match is None
        or int(match["hour"]) > MAX_HOUR
        or int(match["minute"]) > MAX_MINUTE
    ):
        raise _fail(path, "start must be a time of day written HH:MM")


def _validate_meter(path: str, hint: dict[str, object]) -> None:
    _validate_meter_tiers(path, hint.get("tiers"))
    _validate_clamp(path, hint)
    effects = hint.get("effects")
    if effects is not None:
        _validate_effects(path, effects)


def _validate_meter_tiers(path: str, tiers: object) -> None:
    if tiers is None:
        return
    if not isinstance(tiers, list):
        raise _fail(path, "tiers must be a list")
    minimums = [t["min"] for t in tiers if isinstance(t, dict) and "min" in t]
    if any(later >= earlier for earlier, later in pairwise(minimums)):
        raise _fail(path, "tier minimums must strictly descend")


def _validate_clamp(path: str, hint: dict[str, object]) -> None:
    bounds = [hint[key] for key in ("clamp_min", "clamp_max") if key in hint]
    if not all(_is_number(bound) for bound in bounds):
        raise _fail(path, "clamp_min and clamp_max must be numbers")
    if len(bounds) == 2 and bounds[0] >= bounds[1]:  # type: ignore[operator]
        raise _fail(path, "clamp_min must be less than clamp_max")


def _validate_effects(path: str, effects: object) -> None:
    if not isinstance(effects, dict):
        raise _fail(path, "effects must be an object")
    for key in EFFECT_THRESHOLD_KEYS:
        if key in effects and not _is_number(effects[key]):
            raise _fail(path, f"effects {key} must be a number")
    moderate = effects.get("moderate_below")
    critical = effects.get("critical_below")
    if moderate is not None and critical is not None and critical > moderate:
        raise _fail(path, "critical_below must not exceed moderate_below")
    _validate_intrusive_thoughts(path, effects.get("intrusive_thoughts"))


def _validate_intrusive_thoughts(path: str, thoughts: object) -> None:
    if thoughts is None:
        return
    if not isinstance(thoughts, list) or len(thoughts) > MAX_INTRUSIVE_THOUGHTS:
        raise _fail(
            path,
            f"intrusive_thoughts must be a list of at most {MAX_INTRUSIVE_THOUGHTS}",
        )
    if not all(
        isinstance(thought, str) and 0 < len(thought) <= MAX_INTRUSIVE_THOUGHT_LENGTH
        for thought in thoughts
    ):
        raise _fail(
            path,
            f"each intrusive thought must be 1 to {MAX_INTRUSIVE_THOUGHT_LENGTH} characters",
        )


def _validate_hint_counts(hinted: list[tuple[str, dict[str, object]]]) -> None:
    for kind in ("clock", "tier"):
        paths = [p for p, f in hinted if f["display"].get("kind") == kind]  # type: ignore[union-attr]
        if len(paths) > 1:
            raise _fail(paths[1], f"only one {kind} is allowed per scenario")
    with_effects = [
        p
        for p, f in hinted
        if f["display"].get("kind") == "meter" and f["display"].get("effects")  # type: ignore[union-attr]
    ]
    if len(with_effects) > 1:
        raise _fail(with_effects[1], "only one meter may define effects")
