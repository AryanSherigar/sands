"""Engine-owned state for the `rule_sheet` tool.

The tool owns two hidden state roots, `rule_status` and `rule_flags`. They are
injected into the pinned schema (never stored in the creator's schema), reserved
against creator declarations while the tool is on, and accepted as declared by
expression and mutation validation.
"""

from collections.abc import Sequence

from app.exceptions.sheet_rule_exceptions import ReservedStateKeyError
from app.models.sheet_rule import RULE_STATUSES
from app.services.expression_validation import OPEN_KEYS_MARKER

RULE_SHEET_TOOL_KEY = "rule_sheet"
RULE_STATUS_ROOT = "rule_status"
RULE_FLAGS_ROOT = "rule_flags"
RESERVED_ROOTS = (RULE_STATUS_ROOT, RULE_FLAGS_ROOT)


def validate_reserved_roots(
    state_schema: dict[str, object], enabled_tools: Sequence[str]
) -> None:
    if RULE_SHEET_TOOL_KEY not in enabled_tools:
        return
    for root in RESERVED_ROOTS:
        if root in state_schema:
            raise ReservedStateKeyError(
                f"'{root}' is reserved by the Rules & clipboard tool; remove it from "
                "the state schema"
            )


def with_rule_sheet_roots(
    state_schema: dict[str, object], enabled_tools: Sequence[str]
) -> dict[str, object]:
    """The schema validation should see: the creator's fields plus the two roots,
    each an open object (any slug key beneath it counts as declared)."""
    if RULE_SHEET_TOOL_KEY not in enabled_tools:
        return state_schema
    open_root: dict[str, object] = {
        "type": "object",
        "hidden": True,
        "fields": {},
        OPEN_KEYS_MARKER: True,
    }
    return {**state_schema, **dict.fromkeys(RESERVED_ROOTS, open_root)}


def build_schema_extension(
    sheet_rules: Sequence[dict[str, object]],
) -> dict[str, object]:
    """The pinned-schema fields for the given rules; empty when there are none."""
    if not sheet_rules:
        return {}
    statuses = {
        str(rule["key"]): {
            "type": "enum",
            "options": list(RULE_STATUSES),
            "initial": rule["initial_status"],
        }
        for rule in sheet_rules
    }
    extension: dict[str, object] = {
        RULE_STATUS_ROOT: {"type": "object", "hidden": True, "fields": statuses}
    }
    flags = {
        str(rule["key"]): {"type": "boolean", "initial": False}
        for rule in sheet_rules
        if rule.get("is_ai_flaggable")
    }
    if flags:
        extension[RULE_FLAGS_ROOT] = {
            "type": "object",
            "hidden": True,
            "fields": flags,
        }
    return extension
