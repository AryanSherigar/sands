"""Flags strategy action blocks that would fail or be nonsense when applied."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from app.models.assistant import AssistantStrategyContext

MAX_TITLE_LENGTH = 255
MIN_OPINION = -100
MAX_OPINION = 100
MAX_PERCENT = 100
MAX_CONDITIONAL_PERCENT = 200
MONTHS_PER_YEAR = 12
VALID_RELATION_STATUSES = frozenset({"war", "peace", "alliance"})
VALID_TROOP_TYPES = frozenset({"infantry", "cavalry", "archers_siege"})
VALID_RULE_KEYS = frozenset(
    {
        "agents_enabled",
        "revolt_talks_enabled",
        "bribe_base_price",
        "trade_value_per_turn",
        "trade_income_percent",
        "access_value_per_turn",
        "conditional_trigger_percent",
        "conditional_gate_percent",
        "oath_offer_min_opinion",
        "oath_offer_duration_turns",
        "letters_enabled",
        "letter_cooldown_turns",
        "judgments_enabled",
        "judgment_cooldown_turns",
        "judgment_sentence_turns",
    }
)
BOOLEAN_RULE_KEYS = frozenset(
    {"agents_enabled", "revolt_talks_enabled", "letters_enabled", "judgments_enabled"}
)
POSITIVE_RULE_KEYS = (
    "trade_value_per_turn",
    "trade_income_percent",
    "access_value_per_turn",
    "oath_offer_duration_turns",
    "letter_cooldown_turns",
    "judgment_cooldown_turns",
    "judgment_sentence_turns",
)
MAX_WHOLE_NUMBER = 1_000_000_000
LEADER_ALIAS_SUFFIX = "_ruler"
STRATEGY_JSON_TARGETS = frozenset(
    {
        "faction",
        "leader_history",
        "relation",
        "claim",
        "grudge",
        "region_setup",
        "army",
        "timing",
        "rules",
    }
)


@dataclass
class KnownIds:
    factions: set[str] = field(default_factory=set)
    leaders: set[str] = field(default_factory=set)
    regions: set[str] = field(default_factory=set)


Payload = dict[str, object]


def _build_known_ids(context: AssistantStrategyContext) -> KnownIds:
    return KnownIds(
        factions={f.faction_id for f in context.factions},
        leaders={f.leader_id for f in context.factions if f.leader_id},
        regions={r.region_id for r in context.regions},
    )


def _check_ref(label: str, value: object, known: set[str]) -> list[str]:
    if isinstance(value, str) and value in known:
        return []
    return [f"{label} '{value}' is not an existing id or a temp_id from this reply."]


def _check_optional_ref(label: str, value: object, known: set[str]) -> list[str]:
    if value is None:
        return []
    return _check_ref(label, value, known)


def _check_range(label: str, value: object, low: int, high: int) -> list[str]:
    if value is None:
        return []
    if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
        return []
    return [f"{label} must be a whole number from {low} to {high}."]


def _validate_faction(payload: Payload, known: KnownIds) -> list[str]:
    errors: list[str] = []
    if not str(payload.get("name") or "").strip():
        errors.append("A faction needs a name.")
    errors += _check_optional_ref(
        "capital_region_id", payload.get("capital_region_id"), known.regions
    )
    for key in ("treasury", "manpower"):
        errors += _check_range(key, payload.get(key), 0, MAX_WHOLE_NUMBER)
    return errors + _check_range("stability", payload.get("stability"), 0, MAX_PERCENT)


def _validate_leader_history(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_ref("leader_id", payload.get("leader_id"), known.leaders)
    if not isinstance(payload.get("history"), str):
        errors.append("history must be text.")
    return errors


def _validate_relation(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_ref("faction_a", payload.get("faction_a"), known.factions)
    errors += _check_ref("faction_b", payload.get("faction_b"), known.factions)
    if payload.get("faction_a") == payload.get("faction_b"):
        errors.append("A relation needs two different factions.")
    if payload.get("status") not in VALID_RELATION_STATUSES:
        errors.append("status must be war, peace or alliance.")
    return errors


def _validate_claim(payload: Payload, known: KnownIds) -> list[str]:
    return _check_ref("faction_id", payload.get("faction_id"), known.factions) + (
        _check_ref("region_id", payload.get("region_id"), known.regions)
    )


def _validate_grudge(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_ref("holder_id", payload.get("holder_id"), known.leaders)
    errors += _check_ref("target_id", payload.get("target_id"), known.leaders)
    if payload.get("holder_id") == payload.get("target_id"):
        errors.append("A leader cannot hold a grudge against themselves.")
    return errors + _check_range(
        "opinion", payload.get("opinion"), MIN_OPINION, MAX_OPINION
    )


def _validate_region_setup(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_ref("region_id", payload.get("region_id"), known.regions)
    errors += _check_optional_ref("owner_id", payload.get("owner_id"), known.factions)
    for key in ("population", "wealth", "manpower", "garrison"):
        errors += _check_range(key, payload.get(key), 0, MAX_WHOLE_NUMBER)
    return errors + _check_range("unrest", payload.get("unrest"), 0, MAX_PERCENT)


def _validate_army(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_ref("owner_id", payload.get("owner_id"), known.factions)
    errors += _check_ref("location_id", payload.get("location_id"), known.regions)
    troops = payload.get("troops")
    if not isinstance(troops, dict) or not set(troops) <= VALID_TROOP_TYPES:
        errors.append("troops must use only infantry, cavalry and archers_siege.")
        return errors
    for troop_type, count in troops.items():
        errors += _check_range(f"troops.{troop_type}", count, 0, MAX_WHOLE_NUMBER)
    return errors


def _validate_timing(payload: Payload, known: KnownIds) -> list[str]:
    errors = _check_range("start_month", payload.get("start_month"), 1, MONTHS_PER_YEAR)
    start_year = payload.get("start_year")
    end_year = payload.get("end_year")
    for key, year in (("start_year", start_year), ("end_year", end_year)):
        errors += _check_range(key, year, 0, MAX_WHOLE_NUMBER)
    is_numeric = isinstance(start_year, int) and isinstance(end_year, int)
    if is_numeric and end_year <= start_year:  # type: ignore[operator]
        errors.append("end_year must be after start_year.")
    return errors


def _validate_rules(payload: Payload, known: KnownIds) -> list[str]:
    unknown_keys = sorted(set(payload) - VALID_RULE_KEYS)
    errors = [f"Unknown rule '{key}'." for key in unknown_keys]
    for key in ("conditional_trigger_percent", "conditional_gate_percent"):
        errors += _check_range(key, payload.get(key), 0, MAX_CONDITIONAL_PERCENT)
    for key in POSITIVE_RULE_KEYS:
        errors += _check_range(key, payload.get(key), 1, MAX_WHOLE_NUMBER)
    for key in sorted(BOOLEAN_RULE_KEYS & set(payload)):
        if not isinstance(payload[key], bool):
            errors.append(f"{key} must be true or false.")
    return errors


_VALIDATORS: dict[str, Callable[[Payload, KnownIds], list[str]]] = {
    "faction": _validate_faction,
    "leader_history": _validate_leader_history,
    "relation": _validate_relation,
    "claim": _validate_claim,
    "grudge": _validate_grudge,
    "region_setup": _validate_region_setup,
    "army": _validate_army,
    "timing": _validate_timing,
    "rules": _validate_rules,
}


def _register_new_faction(payload: Payload, known: KnownIds) -> None:
    temp_id = str(payload["temp_id"])
    known.factions.add(temp_id)
    known.leaders.add(f"{temp_id}{LEADER_ALIAS_SUFFIX}")


def _validate_block(target: str, content: str, known: KnownIds) -> list[str]:
    if target == "title":
        length = len(content.strip())
        too_long = f"Title is {length} characters; the limit is {MAX_TITLE_LENGTH}."
        return [too_long] if length > MAX_TITLE_LENGTH else []
    if target not in STRATEGY_JSON_TARGETS:
        return []
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return ["Suggestion is not valid JSON."]
    if not isinstance(payload, dict):
        return ["Suggestion must be a JSON object."]
    if target == "faction" and payload.get("temp_id"):
        _register_new_faction(payload, known)
    return _VALIDATORS[target](payload, known)


def find_strategy_validations(
    blocks: list[tuple[int, str, str]], context: AssistantStrategyContext
) -> list[dict[str, object]]:
    """Takes (index, target, content) for every action block in the reply, in
    order, so a temp_id introduced by an earlier faction block is known to
    later ones. Returns only the blocks with errors."""
    known = _build_known_ids(context)
    results: list[dict[str, object]] = []
    for index, target, content in blocks:
        errors = _validate_block(target, content, known)
        if errors:
            results.append({"index": index, "errors": errors})
    return results
