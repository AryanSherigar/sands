"""The facts block: what the narrator must not contradict this turn.

It sits in the volatile tail of the prompt, after recalled memory and before
the directives, so it never disturbs the cached prefix
(docs/adr/021-prompt-prefix-stability.md). All of it is derived from the pinned
snapshot: a clock display hint, state fields flagged `narrator_fact`, entity
attributes flagged `is_narrator_visible`, and conditions placed in the facts
block (never-describe items; the condition expression says when they apply).
"""

import math
from dataclasses import dataclass

import structlog
from app.config import settings
from app.turn import state_paths
from app.turn.expression_evaluator import evaluate
from app.turn.rule_sheet_view import rule_sheet_view

logger = structlog.get_logger()

EVENT_FACTS_BLOCK_TRUNCATED = "facts_block_truncated"
HEADING = "## Established Facts (do not contradict)"
KEY_NARRATOR_FACT = "narrator_fact"
KEY_DISPLAY = "display"
DISPLAY_KIND_CLOCK = "clock"
PLACEMENT_FACTS = "facts"
STATE_KEY_CURRENT_LOCATION = "current_location_id"
STATE_KEY_RULE_STATUS = "rule_status"
ATTRIBUTE_FLAG_NARRATOR_VISIBLE = "is_narrator_visible"
CLOCK_START_SEPARATOR = ":"
MINUTES_PER_DAY = 1440
MINUTES_PER_HOUR = 60
HOURS_ON_CLOCK_FACE = 12

PRIORITY_ANCHOR = 0
PRIORITY_NEVER_DESCRIBE = 1
PRIORITY_RULES = 2
PRIORITY_STATE_FACTS = 3
PRIORITY_ENTITY_ATTRIBUTES = 4


@dataclass(frozen=True)
class _FactLine:
    text: str
    priority: int


def is_fact_condition(condition: dict[str, object]) -> bool:
    """A condition whose instruction is delivered through the facts block, not
    as a turn directive."""
    metadata = condition.get("metadata")
    return isinstance(metadata, dict) and metadata.get("placement") == PLACEMENT_FACTS


def build_facts_block(snapshot: dict[str, object], state: dict[str, object]) -> str:
    """Empty when the scenario authors no facts and nothing is tracked."""
    schema = snapshot.get("state_schema")
    state_schema = schema if isinstance(schema, dict) else {}
    names = _entity_names(snapshot)
    lines = [
        *_location_and_clock_lines(state_schema, state, names),
        *_rule_status_lines(snapshot, state),
        *_state_fact_lines(state_schema, state),
        *_entity_attribute_lines(snapshot, state),
        *_never_describe_lines(snapshot, state),
    ]
    kept = _fit_to_budget(lines)
    if not kept:
        return ""
    return HEADING + "\n" + "\n".join(line.text for line in kept)


def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / settings.prompt_chars_per_token)


def _fit_to_budget(lines: list[_FactLine]) -> list[_FactLine]:
    kept = list(lines)
    total = sum(_estimate_tokens(line.text) for line in kept)
    droppable = sorted(
        (line for line in kept if line.priority > PRIORITY_ANCHOR),
        key=lambda line: line.priority,
        reverse=True,
    )
    dropped_count = 0
    for line in droppable:
        if total <= settings.facts_block_tokens:
            break
        kept.remove(line)
        total -= _estimate_tokens(line.text)
        dropped_count += 1
    if dropped_count:
        logger.info(EVENT_FACTS_BLOCK_TRUNCATED, dropped_count=dropped_count)
    return kept


def _entity_names(snapshot: dict[str, object]) -> dict[str, str]:
    return {
        str(entity.get("entity_id")): str(entity.get("canonical_name") or "")
        for entity in snapshot.get("entities", []) or []
        if isinstance(entity, dict)
    }


def _location_and_clock_lines(
    state_schema: dict[str, object], state: dict[str, object], names: dict[str, str]
) -> list[_FactLine]:
    lines: list[_FactLine] = []
    location = names.get(str(state.get(STATE_KEY_CURRENT_LOCATION)))
    if location:
        lines.append(_FactLine(f"Location: {location}", PRIORITY_ANCHOR))
    clock = _clock_text(state_schema, state)
    if clock:
        lines.append(_FactLine(f"Clock: {clock}", PRIORITY_ANCHOR))
    return lines


def _clock_text(
    state_schema: dict[str, object], state: dict[str, object]
) -> str | None:
    for name, field_def in sorted(state_schema.items()):
        display = field_def.get(KEY_DISPLAY) if isinstance(field_def, dict) else None
        if isinstance(display, dict) and display.get("kind") == DISPLAY_KIND_CLOCK:
            return _format_clock(display.get("start"), state.get(name))
    return None


def _format_clock(start: object, elapsed: object) -> str | None:
    if not isinstance(start, str) or not isinstance(elapsed, int | float):
        return None
    hours, separator, minutes = start.partition(CLOCK_START_SEPARATOR)
    if not separator or not hours.isdigit() or not minutes.isdigit():
        return None
    total = (
        int(hours) * MINUTES_PER_HOUR + int(minutes) + int(elapsed)
    ) % MINUTES_PER_DAY
    hour, minute = divmod(total, MINUTES_PER_HOUR)
    suffix = "AM" if hour < HOURS_ON_CLOCK_FACE else "PM"
    return f"{hour % HOURS_ON_CLOCK_FACE or HOURS_ON_CLOCK_FACE}:{minute:02d} {suffix}"


def _rule_status_lines(
    snapshot: dict[str, object], state: dict[str, object]
) -> list[_FactLine]:
    sheet_rules = snapshot.get("sheet_rules")
    rule_status = state.get(STATE_KEY_RULE_STATUS)
    if not isinstance(sheet_rules, list):
        return []
    view = rule_sheet_view(
        [rule for rule in sheet_rules if isinstance(rule, dict)],
        rule_status if isinstance(rule_status, dict) else {},
    )
    if not view:
        return []
    summary = ", ".join(f"Rule {item['number']} {item['status']}" for item in view)
    return [_FactLine(f"Rule statuses: {summary}", PRIORITY_RULES)]


def _state_fact_lines(
    state_schema: dict[str, object], state: dict[str, object]
) -> list[_FactLine]:
    lines: list[_FactLine] = []
    for path, label in _flagged_fields(state_schema):
        value = state_paths.get_field_value(state, path)
        if value is not None:
            lines.append(_FactLine(f"{label}: {_render(value)}", PRIORITY_STATE_FACTS))
    return lines


def _flagged_fields(
    fields: dict[str, object], prefix: str = ""
) -> list[tuple[str, str]]:
    flagged: list[tuple[str, str]] = []
    for name, field_def in sorted(fields.items()):
        if not isinstance(field_def, dict):
            continue
        label = field_def.get(KEY_NARRATOR_FACT)
        if isinstance(label, str) and label:
            flagged.append((f"{prefix}{name}", label))
        nested = field_def.get("fields")
        if isinstance(nested, dict):
            flagged.extend(_flagged_fields(nested, f"{prefix}{name}."))
    return flagged


def _entity_attribute_lines(
    snapshot: dict[str, object], state: dict[str, object]
) -> list[_FactLine]:
    bucket = state.get("entities")
    values_by_entity = bucket if isinstance(bucket, dict) else {}
    lines: list[_FactLine] = []
    for entity in snapshot.get("entities", []) or []:
        if not isinstance(entity, dict):
            continue
        values = values_by_entity.get(str(entity.get("entity_id")))
        if isinstance(values, dict):
            lines.extend(_visible_attribute_lines(entity, values))
    return lines


def _visible_attribute_lines(
    entity: dict[str, object], values: dict[str, object]
) -> list[_FactLine]:
    schema = entity.get("attributes_schema")
    if not isinstance(schema, dict):
        return []
    return [
        _FactLine(
            f"{entity.get('canonical_name')} {field_def.get('label') or name}: "
            f"{_render(values[name])}",
            PRIORITY_ENTITY_ATTRIBUTES,
        )
        for name, field_def in sorted(schema.items())
        if isinstance(field_def, dict)
        and field_def.get(ATTRIBUTE_FLAG_NARRATOR_VISIBLE)
        and name in values
    ]


def _never_describe_lines(
    snapshot: dict[str, object], state: dict[str, object]
) -> list[_FactLine]:
    conditions = snapshot.get("scenario_conditions", []) or []
    return [
        _FactLine(str(condition["narrator_instruction"]), PRIORITY_NEVER_DESCRIBE)
        for condition in conditions
        if isinstance(condition, dict)
        and is_fact_condition(condition)
        and condition.get("narrator_instruction")
        and evaluate(condition.get("condition_expression"), state)
    ]


def _render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
