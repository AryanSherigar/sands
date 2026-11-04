"""Structural checks on authored conditions that the Core API validators skip.

Existence of state paths is judged by the Core API's own validators, so a
generator can never accept something the services would refuse. What those do not
look at (operators, enum membership, numeric operations, labels) is checked here.
"""

import uuid
from collections.abc import Callable, Iterator, Sequence

from app.db.models.entity import Entity
from app.exceptions.base import BaseAppException
from app.models.condition import ConditionCreate
from app.services.expression_validation import (
    validate_expression_field_references,
    validate_mutation_paths,
)
from app.services.state_schema_paths import enum_option_values
from scripts.seeding.fields import FieldDef

CONNECTIVES = ("AND", "OR", "NOT")
LEAF_OPS = frozenset({"==", "!=", "<", "<=", ">", ">=", "in", "contains", "matches"})
NUMERIC_OPS = frozenset({"<", "<=", ">", ">="})
MUTATION_OPS = frozenset({"set", "increment", "decrement"})
LOCATION_ENTITY_TYPE = "location"
LOCATION_FIELDS: dict[str, FieldDef] = {
    "current_location_id": {"type": "entity_ref", "entity_type": LOCATION_ENTITY_TYPE},
    "discovered_location_ids": {
        "type": "list",
        "item_type": "entity_ref",
        "entity_type": LOCATION_ENTITY_TYPE,
    },
}


class ProblemError(BaseAppException):
    """Carries one validator complaint back to the problem list."""


def problem(message: str) -> ProblemError:
    return ProblemError(message)


def collect(check: Callable[[], None]) -> list[str]:
    try:
        check()
    except BaseAppException as error:
        return [error.message]
    return []


def nodes(expression: object) -> Iterator[dict[str, object]]:
    while isinstance(expression, dict):
        yield expression
        nested = [expression[name] for name in CONNECTIVES if name in expression]
        if not nested:
            return
        expression = nested[0]


def enum_problems(path: str, op: str, value: object, definition: FieldDef) -> list[str]:
    options = enum_option_values(definition.get("options"))
    values = value if isinstance(value, list) else [value]
    unknown = [item for item in values if item not in options]
    if op in {"==", "!=", "in"} and unknown and value is not None:
        return [f"{path} compared to {unknown} not in options {options}"]
    return []


def value_problems(
    path: str,
    op: str,
    value: object,
    definition: FieldDef,
    entity_ids: set[str],
    entity_ref_paths: Sequence[str],
) -> list[str]:
    kind = definition.get("type")
    if op in NUMERIC_OPS and kind != "number":
        return [f"numeric op {op} on non-number field {path}"]
    if kind == "enum":
        return enum_problems(path, op, value, definition)
    if path in entity_ref_paths and isinstance(value, str) and value not in entity_ids:
        return [f"{path} compares to unknown entity id {value}"]
    return []


class ConditionChecker:
    """Checks expressions and mutations against a schema and its entities.

    `fields` maps every readable path (state leaves and `<entity id>.<attribute>`)
    to its definition.
    """

    def __init__(
        self,
        schema: dict[str, object],
        fields: dict[str, FieldDef],
        entities: dict[uuid.UUID, Entity],
        entity_ref_paths: Sequence[str] = (),
    ) -> None:
        self.schema = schema
        self.fields = fields
        self.entities = entities
        self.entity_ids = {str(key) for key in entities}
        self.entity_ref_paths = entity_ref_paths

    def _leaf_problems(self, node: dict[str, object]) -> list[str]:
        if "field" not in node:
            return []
        path, op = str(node["field"]), str(node.get("op", "=="))
        found = [f"unknown op {op!r} on {path}"] if op not in LEAF_OPS else []
        if path not in self.fields:
            return [*found, f"unknown field path {path!r}"]
        return [
            *found,
            *value_problems(
                path,
                op,
                node.get("value"),
                self.fields[path],
                self.entity_ids,
                self.entity_ref_paths,
            ),
        ]

    def expression_problems(self, expression: object, owner: str) -> list[str]:
        found = collect(
            lambda: validate_expression_field_references(
                expression,  # type: ignore[arg-type]
                self.schema,
                self.entities,  # type: ignore[arg-type]
                problem,
            )
        )
        for node in nodes(expression):
            if len([name for name in CONNECTIVES if name in node]) > 1:
                found.append("node has more than one connective")
            found.extend(self._leaf_problems(node))
        return [f"{owner}: {item}" for item in found]

    def mutation_problems(self, mutations: Sequence[object], owner: str) -> list[str]:
        paths = [str(mutation.path) for mutation in mutations]
        found = collect(
            lambda: validate_mutation_paths(
                paths,
                self.schema,
                self.entities,  # type: ignore[arg-type]
                problem,
            )
        )
        for mutation in mutations:
            found.extend(self._mutation_value_problems(mutation))
        return [f"{owner}: {item}" for item in found]

    def _mutation_value_problems(self, mutation: object) -> list[str]:
        path = str(mutation.path)
        op, value = str(mutation.op), mutation.value
        definition = self.fields.get(path)
        if op not in MUTATION_OPS:
            return [f"mutation op {op!r} invalid"]
        if definition is None:
            return []
        if op != "set" and definition.get("type") != "number":
            return [f"{op} on non-number {path}"]
        if definition.get("type") == "enum" and op == "set":
            options = enum_option_values(definition.get("options"))
            if value not in options:
                return [f"set {path}={value!r} not in {options}"]
        return []


def label_problems(conditions: Sequence[ConditionCreate]) -> list[str]:
    seen: set[str] = set()
    found: list[str] = []
    for condition in conditions:
        if condition.label in seen:
            found.append(f"duplicate label {condition.label!r}")
        seen.add(condition.label)
    return found


def effect_problems(conditions: Sequence[ConditionCreate]) -> list[str]:
    return [
        f"condition {item.label!r} has no mutation, instruction, cue or effect"
        for item in conditions
        if not (
            item.state_mutations
            or item.narrator_instruction
            or item.sensory_cue
            or item.metadata.get("client_effect")
            or item.metadata.get("authored_image_url")
        )
    ]


def order_problems(
    conditions: Sequence[ConditionCreate], group_order: Sequence[str]
) -> list[str]:
    ranks = [group_order.index(item.label[0]) for item in conditions]
    return [
        f"condition {conditions[i].label!r} breaks group order"
        for i in range(1, len(ranks))
        if ranks[i] < ranks[i - 1]
    ]
