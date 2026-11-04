"""Structural checks on the built Zegaris scenario. Returns problems; never raises.

Path existence and schema flags are judged by the Core API's own validators.
This adds operator and enum checks, plus the fantasy profile and combat
encounters, because publish-time combat validation does not exist yet.
"""

from collections.abc import Sequence

from app.db.models.entity import Entity
from app.models.condition import ConditionCreate
from app.models.content_tags import validate_content_tags
from app.services.fantasy_setup import apply_fantasy_setup
from app.services.schema_field_validation import validate_schema_fields
from app.tools.registry import close_over_requires
from scripts.seeding.fields import flatten_schema
from scripts.seeding.validation import (
    LOCATION_FIELDS,
    ConditionChecker,
    collect,
    effect_problems,
    label_problems,
    order_problems,
    problem,
)
from scripts.zegaris.builder import ZegarisScenario
from scripts.zegaris.conditions.common import GROUP_ORDER
from scripts.zegaris.ids import SCENARIO_ID, entity_id
from scripts.zegaris.mechanics import CLASS_LOADOUTS

ENTITY_REF_PATHS = ("current_location_id", "player.inventory")
STAT_KEYS = ("max_health", "health", "attack", "armor", "speed", "accuracy", "luck")
STAT_CEILING = 10000
PERCENT_KEYS = ("accuracy", "luck")
PERCENT_CEILING = 100


def pinned_schema(built: ZegarisScenario) -> dict[str, object]:
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    return {**creator, **LOCATION_FIELDS}


def _entities(built: ZegarisScenario) -> dict[object, Entity]:
    return {
        entity_id(seed.slug): Entity(
            entity_id=entity_id(seed.slug),
            scenario_id=SCENARIO_ID,
            entity_type=seed.payload.entity_type,
            canonical_name=seed.payload.canonical_name,
            attributes_schema={},
        )
        for seed in built.entities
    }


def _checker(built: ZegarisScenario) -> ConditionChecker:
    schema = pinned_schema(built)
    return ConditionChecker(
        schema,
        flatten_schema(schema),  # type: ignore[arg-type]
        _entities(built),  # type: ignore[arg-type]
        ENTITY_REF_PATHS,
    )


def _condition_problems(
    checker: ConditionChecker, conditions: Sequence[ConditionCreate]
) -> list[str]:
    found: list[str] = []
    for condition in conditions:
        found += checker.expression_problems(
            condition.condition_expression, condition.label
        )
        found += checker.mutation_problems(condition.state_mutations, condition.label)
    return found


def _scenario_problems(built: ZegarisScenario) -> list[str]:
    tools: list[str] = built.scenario["enabled_tools"]  # type: ignore[assignment]
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    found = collect(lambda: _ensure_tools_closed(tools))
    found += collect(lambda: validate_schema_fields(creator, tools))
    tags: list[str] = built.scenario["content_tags"]  # type: ignore[assignment]
    try:
        validate_content_tags(tags)
    except ValueError as error:
        found.append(str(error))
    genres: list[str] = built.scenario["genre_tags"]  # type: ignore[assignment]
    if genres[:1] != ["High Fantasy"]:
        found.append("the first genre tag must be 'High Fantasy' to use the reader")
    return found


def _ensure_tools_closed(tools: list[str]) -> None:
    closed, added = close_over_requires(tools)
    if added or closed != tools:
        raise problem(f"enabled_tools is not closed over requires: {tools}")


def _combatant_problems(owner: str, actor: dict[str, object]) -> list[str]:
    found: list[str] = []
    for key in STAT_KEYS:
        value = actor.get(key)
        ceiling = PERCENT_CEILING if key in PERCENT_KEYS else STAT_CEILING
        if type(value) is not int or not 0 <= value <= ceiling:
            found.append(f"{owner}: {key}={value!r} out of range")
    if type(actor.get("health")) is int and actor["health"] > actor["max_health"]:  # type: ignore[operator]
        found.append(f"{owner}: health exceeds max_health")
    return found


def _damage_problems(owner: str, encounter: dict[str, object]) -> list[str]:
    player: dict[str, object] = encounter["player"]  # type: ignore[assignment]
    opponent: dict[str, object] = encounter["opponent"]  # type: ignore[assignment]
    required = opponent.get("required_attack_tag")
    if required is not None and required not in player.get("attack_tags", []):  # type: ignore[operator]
        return [f"{owner}: the player cannot damage the opponent"]
    return []


def _outcome_problems(owner: str, encounter: dict[str, object]) -> list[str]:
    outcomes: list[dict[str, object]] = encounter["outcomes"]  # type: ignore[assignment]
    ids = [outcome["id"] for outcome in outcomes]
    found: list[str] = []
    if encounter["fallback_outcome_id"] not in ids or len(set(ids)) != len(ids):
        found.append(f"{owner}: fallback outcome is missing or ids repeat")
    if any(outcome.get("kind") == "end" for outcome in outcomes):
        found.append(f"{owner}: this scenario authors no endings")
    return found


def _combat_problems(built: ZegarisScenario, checker: ConditionChecker) -> list[str]:
    rules: dict[str, object] = built.scenario["rules"]  # type: ignore[assignment]
    encounters: list[dict[str, object]] = rules["fantasy_combat"]["encounters"]  # type: ignore[index]
    entity_ids = {str(entity_id(seed.slug)) for seed in built.entities}
    found: list[str] = []
    for encounter in encounters:
        owner = f"encounter {encounter['encounter_id']}"
        found += checker.expression_problems(encounter["start_condition"], owner)
        found += _combatant_problems(owner, encounter["player"])  # type: ignore[arg-type]
        found += _combatant_problems(owner, encounter["opponent"])  # type: ignore[arg-type]
        found += _damage_problems(owner, encounter)
        found += _outcome_problems(owner, encounter)
        for outcome in encounter["outcomes"]:  # type: ignore[attr-defined]
            location = outcome.get("location_id")
            if location is not None and location not in entity_ids:
                found.append(f"{owner}: recovery location is not an entity")
    return found


def _profile_problems(built: ZegarisScenario) -> list[str]:
    snapshot = {
        **built.scenario["rules"],  # type: ignore[dict-item]
        "entities": [
            {
                "entity_id": str(entity_id(seed.slug)),
                "entity_type": seed.payload.entity_type,
            }
            for seed in built.entities
        ],
    }
    found: list[str] = []
    for key in CLASS_LOADOUTS:
        try:
            apply_fantasy_setup(snapshot, {}, {"outlander_class": key})
        except Exception as error:
            found.append(f"fantasy profile rejects {key}: {error}")
    return found


def validate(built: ZegarisScenario) -> list[str]:
    checker = _checker(built)
    conditions = built.conditions
    return [
        *_scenario_problems(built),
        *order_problems(conditions, GROUP_ORDER),
        *label_problems(conditions),
        *effect_problems(conditions),
        *_condition_problems(checker, conditions),
        *_combat_problems(built, checker),
        *_profile_problems(built),
    ]
