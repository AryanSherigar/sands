"""Structural checks on a built scenario. Returns problems; never raises.

Existence of state paths, display hints, hidden/random fields and rule-check
params is judged by the Core API's own validators, so the generator can never
accept something the services would refuse. What those validators do not look at
(enum membership, numeric ops, group order) is checked here.
"""

from app.db.models.entity import Entity
from app.models.client_effect import validate_condition_metadata
from app.models.condition import ConditionCreate
from app.models.content_tags import validate_content_tags
from app.models.rule_check import PARAMS_MODELS, RuleCheckCreate
from app.services.display_hints import validate_display_hints
from app.services.rule_sheet_state import (
    build_schema_extension,
    validate_reserved_roots,
)
from app.services.schema_field_validation import validate_schema_fields
from app.services.state_schema_paths import enum_option_values, field_at_path
from app.tools.registry import close_over_requires
from scripts.night_desk import timeline
from scripts.night_desk.builder import GROUP_ORDER, NightDeskScenario
from scripts.night_desk.ids import SCENARIO_ID, entity_id
from scripts.night_desk.schema import flatten_schema
from scripts.seeding.validation import (
    LOCATION_FIELDS,
    ConditionChecker,
    effect_problems,
    label_problems,
)
from scripts.seeding.validation import (
    collect as _collect,
)
from scripts.seeding.validation import nodes as _nodes  # noqa: F401
from scripts.seeding.validation import (
    order_problems as shared_order_problems,
)
from scripts.seeding.validation import (
    problem as _problem,
)

ENTITY_REF_PATHS = ("current_location_id", "player.inventory")


def pinned_schema(built: NightDeskScenario) -> dict[str, object]:
    """The state schema a playthrough pins: the creator's fields, the two
    system-provisioned location fields and the rule sheet's status roots."""
    rules = [
        {
            "key": rule.key,
            "initial_status": rule.initial_status,
            "is_ai_flaggable": rule.is_ai_flaggable,
        }
        for rule in built.sheet_rules
    ]
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    return {**creator, **LOCATION_FIELDS, **build_schema_extension(rules)}


def _entities(built: NightDeskScenario) -> dict[object, Entity]:
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


class _Context(ConditionChecker):
    def __init__(self, built: NightDeskScenario) -> None:
        schema = pinned_schema(built)
        super().__init__(
            schema,
            flatten_schema(schema),  # type: ignore[arg-type]
            _entities(built),  # type: ignore[arg-type]
            ENTITY_REF_PATHS,
        )


def order_problems(conditions: list[ConditionCreate]) -> list[str]:
    return shared_order_problems(conditions, GROUP_ORDER)


def _effect_metadata_problems(conditions: list[ConditionCreate]) -> list[str]:
    problems: list[str] = []
    for condition in conditions:
        try:
            validate_condition_metadata(condition.metadata)
        except ValueError as error:
            problems.append(f"condition {condition.label!r}: {error}")
    return problems


def _r6_rows_problems(built: NightDeskScenario) -> list[str]:
    styles = sorted(rule.source_style for rule in built.sheet_rules if rule.number == 6)
    if styles != ["ink", "ink_block"]:
        return [f"rule 6 must have one ink and one ink_block row, found {styles}"]
    return []


def _turn_count_problems() -> list[str]:
    if timeline.turns_to_dawn() != timeline.EXPECTED_TURN_COUNT:
        return [
            f"the night is {timeline.turns_to_dawn()} turns, "
            f"expected {timeline.EXPECTED_TURN_COUNT}"
        ]
    return []


def _tool_problems(built: NightDeskScenario) -> list[str]:
    tools: list[str] = built.scenario["enabled_tools"]  # type: ignore[assignment]
    creator: dict[str, object] = built.scenario["state_schema"]  # type: ignore[assignment]
    problems = _collect(lambda: _ensure_tools_closed(tools))
    problems += _collect(lambda: validate_reserved_roots(creator, tools))
    problems += _collect(lambda: validate_schema_fields(creator, tools))
    problems += _collect(lambda: validate_display_hints(creator, tools))
    return problems


def _content_tag_problems(built: NightDeskScenario) -> list[str]:
    tags: list[str] = built.scenario["content_tags"]  # type: ignore[assignment]
    try:
        validate_content_tags(tags)
    except ValueError as error:
        return [str(error)]
    return []


def _ensure_tools_closed(tools: list[str]) -> None:
    closed, added = close_over_requires(tools)
    if added or closed != tools:
        raise _problem(f"enabled_tools is not closed over requires: {tools}")


def _condition_problems(
    context: _Context, conditions: list[ConditionCreate]
) -> list[str]:
    problems: list[str] = []
    for condition in conditions:
        owner = condition.label
        problems.extend(
            context.expression_problems(condition.condition_expression, owner)
        )
        problems.extend(context.mutation_problems(condition.state_mutations, owner))
    return problems


def _check_problems(context: _Context, checks: list[RuleCheckCreate]) -> list[str]:
    problems: list[str] = []
    for check in checks:
        owner = f"rule check {check.label!r}"
        params = PARAMS_MODELS[check.kind].model_validate(check.params)
        problems.extend(
            context.expression_problems(check.trigger_condition_expression, owner)
        )
        problems.extend(_result_problems(context, check, params.result_values(), owner))
        problems.extend(_option_mutation_problems(context, check, owner))
    return problems


def _result_problems(
    context: _Context, check: RuleCheckCreate, results: list[str], owner: str
) -> list[str]:
    field = field_at_path(context.schema, check.result_path)
    if field is None or field.get("type") != "enum":
        return [f"{owner}: result_path {check.result_path!r} is not an enum field"]
    allowed = enum_option_values(field.get("options"))
    return [
        f"{owner}: result {result!r} is not an option of {check.result_path}"
        for result in results
        if result not in allowed
    ]


TIME_ENTRY_OUTCOME_KEYS = ("told", "wall", "other", "reject")


def _check_mutation_dicts(check: RuleCheckCreate) -> list[dict[str, object]]:
    options = check.params.get("options")
    blocks = options if isinstance(options, list) else []
    if check.kind == "time_entry":
        blocks = [check.params[key] for key in TIME_ENTRY_OUTCOME_KEYS]
    return [mutation for block in blocks for mutation in block["mutations"]]


def _option_mutation_problems(
    context: _Context, check: RuleCheckCreate, owner: str
) -> list[str]:
    problems: list[str] = []
    for mutation in _check_mutation_dicts(check):
        problems.extend(context.mutation_problems([_Mutation(**mutation)], owner))
    return problems


class _Mutation:
    def __init__(self, path: str, op: str, value: object) -> None:
        self.path, self.op, self.value = path, op, value


def _minigame_problems(context: _Context, built: NightDeskScenario) -> list[str]:
    problems: list[str] = []
    for minigame in built.minigames:
        owner = f"minigame {minigame.label!r}"
        problems.extend(
            context.expression_problems(minigame.trigger_condition_expression, owner)
        )
        for outcome in (
            minigame.win_mutations,
            minigame.lose_mutations,
            minigame.timeout_mutations,
        ):
            problems.extend(context.mutation_problems(outcome, owner))
    return problems


def _other_expression_problems(
    context: _Context, built: NightDeskScenario
) -> list[str]:
    problems: list[str] = []
    for ending in built.end_conditions:
        problems.extend(
            context.expression_problems(
                ending.condition_expression, f"ending {ending.outcome_title!r}"
            )
        )
    for invariant in built.invariants:
        problems.extend(
            context.expression_problems(
                invariant.invariant_expression, f"invariant {invariant.label!r}"
            )
        )
    for fact in built.facts:
        if fact.when_active:
            problems.extend(context.expression_problems(fact.when_active, "fact"))
    return problems


def validate(built: NightDeskScenario) -> list[str]:
    context = _Context(built)
    problems = [
        *_tool_problems(built),
        *_content_tag_problems(built),
        *order_problems(built.conditions),
        *label_problems(built.conditions),
        *effect_problems(built.conditions),
        *_effect_metadata_problems(built.conditions),
        *_r6_rows_problems(built),
        *_turn_count_problems(),
        *_condition_problems(context, built.conditions),
        *_check_problems(context, built.rule_checks),
        *_minigame_problems(context, built),
        *_other_expression_problems(context, built),
    ]
    return problems
