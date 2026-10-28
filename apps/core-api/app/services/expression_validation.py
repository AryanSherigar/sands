"""Shared field-reference validation for condition/invariant expression trees.

Used by ConditionService, EndConditionService, and InvariantService to reject
an expression referencing a field path that doesn't exist in the owning
scenario's state_schema or in one of its entities' attributes_schema — before
anything is persisted (master-mode-data-model.spec.md).

This is an authoring-time existence check only (does the root field exist at
all), not full nested-type validation — that's the runtime job of TRS's
dynamically-built Pydantic model (master-mode-turn-pipeline.spec.md).
"""

import re
import uuid
from collections.abc import Callable

from app.db.models.entity import Entity
from app.exceptions.base import BaseAppException
from app.models.sheet_rule import SHEET_RULE_KEY_PATTERN

OPEN_KEYS_MARKER = "has_open_keys"
_CONNECTIVES = ("AND", "OR", "NOT")
_SLUG = re.compile(SHEET_RULE_KEY_PATTERN)


def validate_expression_field_references(
    expression: dict[str, object] | None,
    state_schema: dict[str, object],
    entities_by_id: dict[uuid.UUID, Entity],
    error_factory: Callable[[str], BaseAppException],
) -> None:
    """Recursively validate every field path in an expression tree.

    error_factory builds the caller's own domain exception (e.g.
    ConditionValidationError, InvariantValidationError) so each domain keeps
    raising its own typed exception rather than a borrowed one.
    """
    if not expression:
        return

    connectives = [c for c in _CONNECTIVES if c in expression]
    if len(connectives) > 1:
        raise error_factory(
            "An expression node may contain at most one connective ('AND', 'OR', 'NOT')"
        )

    field = expression.get("field")
    if field is not None:
        _validate_field_path(str(field), state_schema, entities_by_id, error_factory)

    ref = expression.get("ref")
    if ref is not None:
        _validate_field_path(str(ref), state_schema, entities_by_id, error_factory)

    for connective in connectives:
        nested = expression.get(connective)
        if not isinstance(nested, dict):
            raise error_factory(
                f"Connective '{connective}' must be a nested expression "
                "object, not a list or other type"
            )
        validate_expression_field_references(
            nested, state_schema, entities_by_id, error_factory
        )


def _validate_field_path(
    path: str,
    state_schema: dict[str, object],
    entities_by_id: dict[uuid.UUID, Entity],
    error_factory: Callable[[str], BaseAppException],
) -> None:
    """A field path's root segment must be a state_schema key or an entity ID."""
    root = path.split(".", 1)[0]

    if root in state_schema:
        return
    if _resolves_to_known_entity(root, entities_by_id):
        return

    raise error_factory(
        f"Field '{path}' does not reference a known state_schema field or entity"
    )


def _resolves_to_known_entity(
    root: str, entities_by_id: dict[uuid.UUID, Entity]
) -> bool:
    try:
        return uuid.UUID(root) in entities_by_id
    except ValueError:
        return False


def validate_mutation_paths(
    paths: list[str],
    state_schema: dict[str, object],
    entities_by_id: dict[uuid.UUID, Entity],
    error_factory: Callable[[str], BaseAppException],
) -> None:
    """Every path must resolve fully: a declared state_schema leaf, or a declared
    `<entity_id>.<attribute>`. A write to an undeclared path validates in TRS's
    Pydantic merge and is then silently dropped, so it is refused here."""
    for path in paths:
        if not _is_declared_mutation_path(path, state_schema, entities_by_id):
            raise error_factory(
                f"Mutation path '{path}' is not a declared state_schema field "
                "or entity attribute"
            )


def _is_declared_mutation_path(
    path: str,
    state_schema: dict[str, object],
    entities_by_id: dict[uuid.UUID, Entity],
) -> bool:
    root, *remaining = path.split(".")
    if root in state_schema:
        return _schema_path_exists(state_schema[root], remaining)
    entity = _known_entity(root, entities_by_id)
    return (
        entity is not None
        and len(remaining) == 1
        and remaining[0] in entity.attributes_schema
    )


def _schema_path_exists(field_def: object, remaining: list[str]) -> bool:
    for index, segment in enumerate(remaining):
        if not isinstance(field_def, dict) or field_def.get("type") != "object":
            return False
        nested = field_def.get("fields")
        if not isinstance(nested, dict):
            return False
        if segment not in nested:
            is_last = index == len(remaining) - 1
            return is_last and _is_open_key(field_def, segment)
        field_def = nested[segment]
    return True


def _is_open_key(field_def: dict[str, object], segment: str) -> bool:
    """An open object (the rule sheet's status and flag roots) counts any slug
    beneath it as declared."""
    return field_def.get(OPEN_KEYS_MARKER) is True and bool(_SLUG.match(segment))


def _known_entity(root: str, entities_by_id: dict[uuid.UUID, Entity]) -> Entity | None:
    try:
        return entities_by_id.get(uuid.UUID(root))
    except ValueError:
        return None
