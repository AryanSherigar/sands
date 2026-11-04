"""Structural checks on the built appraisal scenario. Returns problems; never raises.

Path existence, display hints and schema flags are judged by the Core API's own
validators. What they do not look at (operators, enum membership, numeric
operations, the range of a literal write, labels and group order) is checked by
the shared ConditionChecker plus the range check here.
"""

from collections.abc import Sequence

from app.db.models.entity import Entity
from app.models.condition import ConditionCreate
from app.models.content_tags import validate_content_tags
from app.services.display_hints import validate_display_hints
from app.services.schema_field_validation import validate_schema_fields
from app.tools.registry import close_over_requires
from scripts.reincarnated_aristocrat.builder import AppraisalScenario
from scripts.reincarnated_aristocrat.conditions.common import GROUP_ORDER
from scripts.reincarnated_aristocrat.ids import SCENARIO_ID, entity_id
from scripts.seeding.fields import FieldDef, flatten_schema
from scripts.seeding.validation import (
    LOCATION_FIELDS,
    ConditionChecker,
    collect,
    effect_problems,
    label_problems,
    order_problems,
    problem,
)

ENTITY_REF_PATHS = ("current_location_id",)


def pinned_schema(built: AppraisalScenario) -> dict[str, object]:
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    return {**creator, **LOCATION_FIELDS}


def _entities(built: AppraisalScenario) -> dict[object, Entity]:
    return {
        entity_id(seed.slug): Entity(
            entity_id=entity_id(seed.slug),
            scenario_id=SCENARIO_ID,
            entity_type=seed.payload.entity_type,
            canonical_name=seed.payload.canonical_name,
            attributes_schema={
                name: field.model_dump()
                for name, field in seed.payload.attributes_schema.items()
            },
        )
        for seed in built.entities
    }


def _attribute_fields(built: AppraisalScenario) -> dict[str, FieldDef]:
    return {
        f"{entity_id(seed.slug)}.{name}": field.model_dump()
        for seed in built.entities
        for name, field in seed.payload.attributes_schema.items()
    }


def _checker(built: AppraisalScenario) -> ConditionChecker:
    schema = pinned_schema(built)
    fields = {**flatten_schema(schema), **_attribute_fields(built)}  # type: ignore[arg-type]
    return ConditionChecker(
        schema,
        fields,
        _entities(built),  # type: ignore[arg-type]
        ENTITY_REF_PATHS,
    )


def _range_problems(
    conditions: Sequence[ConditionCreate], fields: dict[str, FieldDef]
) -> list[str]:
    found: list[str] = []
    for condition in conditions:
        for mutation in condition.state_mutations:
            definition = fields.get(mutation.path)
            if mutation.op != "set" or definition is None:
                continue
            if definition.get("type") != "number":
                continue
            low, high = definition.get("min"), definition.get("max")
            value = mutation.value
            if (low is not None and value < low) or (high is not None and value > high):  # type: ignore[operator]
                found.append(
                    f"{condition.label}: set {mutation.path}={value} out of range"
                )
    return found


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


def _ending_problems(built: AppraisalScenario, checker: ConditionChecker) -> list[str]:
    found: list[str] = []
    for ending in built.end_conditions:
        found += checker.expression_problems(
            ending.condition_expression, f"ending {ending.outcome_title!r}"
        )
    return found


def _scenario_problems(built: AppraisalScenario) -> list[str]:
    tools: list[str] = built.scenario["enabled_tools"]  # type: ignore[assignment]
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    found = collect(lambda: _ensure_tools_closed(tools))
    found += collect(lambda: validate_schema_fields(creator, tools))
    found += collect(lambda: validate_display_hints(creator, tools))
    tags: list[str] = built.scenario["content_tags"]  # type: ignore[assignment]
    try:
        validate_content_tags(tags)
    except ValueError as error:
        found.append(str(error))
    return found


def _ensure_tools_closed(tools: list[str]) -> None:
    closed, added = close_over_requires(tools)
    if added or closed != tools:
        raise problem(f"enabled_tools is not closed over requires: {tools}")


def validate(built: AppraisalScenario) -> list[str]:
    checker = _checker(built)
    conditions = built.conditions
    return [
        *_scenario_problems(built),
        *order_problems(conditions, GROUP_ORDER),
        *label_problems(conditions),
        *effect_problems(conditions),
        *_condition_problems(checker, conditions),
        *_range_problems(conditions, checker.fields),
        *_ending_problems(built, checker),
    ]
