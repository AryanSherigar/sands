"""Translates a Gemini function call into a proposed state mutation.

Pure computation only — never calls gemini_client (CLAUDE.md: only
ai_orchestrator.py may call it) and never touches Playthrough.state directly
(state_validator.py owns applying + validating). propose_check is handled
separately by ai_orchestrator.py (it never mutates state either, so it
doesn't produce a ProposedMutation at all — see ProposedCheck).
"""

from __future__ import annotations

import random

from app.models.tool_call import ProposedMutation
from google.genai import types

DEFAULT_CHECK_DIE_SIDES = 20


def prepare_mutation(call: types.FunctionCall) -> ProposedMutation:
    """Translate one Gemini function call into a ProposedMutation."""
    args = dict(call.args or {})
    name = call.name or ""

    if name == "set_field":
        return ProposedMutation(
            tool_name=name, op="set", path=args.get("path"), value=args.get("value")
        )
    if name == "adjust_numeric_field":
        return ProposedMutation(
            tool_name=name,
            op="increment",
            path=args.get("path"),
            delta=_to_float(args.get("delta"), default=0.0),
        )
    if name == "add_inventory_item":
        return ProposedMutation(
            tool_name=name,
            op="add_item",
            path=args.get("path"),
            value=args.get("entity_id"),
        )
    return ProposedMutation(tool_name=name, op="unknown")


def compute_roll(
    sides: int = DEFAULT_CHECK_DIE_SIDES, modifier: int = 0
) -> dict[str, object]:
    """Pure dice computation for a check resolution — no state mutation.

    Called directly from check_result_resolver.py, never from a Gemini tool
    call: the roll is server-computed, not model-invoked.
    """
    safe_sides = max(sides, 1)
    roll = random.randint(1, safe_sides)
    return {"roll": roll, "modifier": modifier, "total": roll + modifier}


def _to_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
