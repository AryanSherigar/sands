"""Fixed generic tool set for master-mode Gemini function-calling.

Deliberately generic (not per-scenario dynamic schemas) per the locked
decision — these four tools work against any scenario's state_schema shape.
Discipline against wasteful/trivial calls lives in each description's text,
not a mechanical gate — see docs/specs/master-mode-demo-scenario.md §12 for
a worked example.
"""

from google.genai import types

TOOL_SET_FIELD = types.FunctionDeclaration(
    name="set_field",
    description=(
        "Set a state field to an exact value. Use only when the player's "
        "action would meaningfully and durably change tracked state — never "
        "for flavor/descriptive narration with no lasting effect."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING),
            "value": types.Schema(type=types.Type.STRING),
        },
        required=["path", "value"],
    ),
)

TOOL_ADJUST_NUMERIC_FIELD = types.FunctionDeclaration(
    name="adjust_numeric_field",
    description=(
        "Increment or decrement a numeric field by a delta (e.g. damage, "
        "healing, reputation shifts). Use only for a real, consequential "
        "change — not routine flavor. Use a negative delta to decrease."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING),
            "delta": types.Schema(type=types.Type.NUMBER),
        },
        required=["path", "delta"],
    ),
)

TOOL_ADD_INVENTORY_ITEM = types.FunctionDeclaration(
    name="add_inventory_item",
    description="Add an obtainable item entity to an inventory list field.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING),
            "entity_id": types.Schema(type=types.Type.STRING),
        },
        required=["path", "entity_id"],
    ),
)

TOOL_PROPOSE_CHECK = types.FunctionDeclaration(
    name="propose_check",
    description=(
        "Declare that the player's action calls for a genuinely uncertain, "
        "consequential dice check — a real skill check or contested action. "
        "This does not roll or resolve anything itself: it only flags that a "
        "check is warranted, so end your narration at the moment of tension "
        "and let the player choose whether to attempt it. Never for routine "
        "or narratively assured actions."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "check_type": types.Schema(type=types.Type.STRING),
            "difficulty_class": types.Schema(type=types.Type.INTEGER),
            "reasoning": types.Schema(type=types.Type.STRING),
        },
        required=["check_type", "difficulty_class"],
    ),
)

MASTER_MODE_TOOLS = types.Tool(
    function_declarations=[
        TOOL_SET_FIELD,
        TOOL_ADJUST_NUMERIC_FIELD,
        TOOL_ADD_INVENTORY_ITEM,
        TOOL_PROPOSE_CHECK,
    ]
)


TOOL_FLAG_RULE_VIOLATION_NAME = "flag_rule_violation"
EVIDENCE_MAX_LENGTH = 200
RULE_SHEET_TOOL_KEY = "rule_sheet"


def flaggable_rule_keys(snapshot: dict[str, object]) -> list[str]:
    """Keys of the sheet rules the narrator may report a violation of, in order."""
    if RULE_SHEET_TOOL_KEY not in (snapshot.get("enabled_tools") or []):  # type: ignore[operator]
        return []
    rules = snapshot.get("sheet_rules")
    return [
        str(rule["key"])
        for rule in (rules if isinstance(rules, list) else [])
        if isinstance(rule, dict) and rule.get("is_ai_flaggable") is True
    ]


def _flag_rule_violation_tool(rule_keys: list[str]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=TOOL_FLAG_RULE_VIOLATION_NAME,
        description=(
            "Report that the clerk's action clearly broke one of the rules on the "
            "sheet. Call it only when the action plainly violates that rule as "
            "written; quote the sheet in the evidence and never invent a penalty "
            "or a rule. The game applies the consequence, not you."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "rule_id": types.Schema(type=types.Type.STRING, enum=rule_keys),
                "evidence": types.Schema(
                    type=types.Type.STRING, max_length=str(EVIDENCE_MAX_LENGTH)
                ),
            },
            required=["rule_id", "evidence"],
        ),
    )


def build_master_mode_tools(snapshot: dict[str, object]) -> types.Tool:
    """The static tool set, plus `flag_rule_violation` when the rule sheet is on
    and at least one rule is flaggable."""
    rule_keys = flaggable_rule_keys(snapshot)
    base_declarations = MASTER_MODE_TOOLS.function_declarations or []
    declarations = list(base_declarations)
    if rule_keys:
        declarations.append(_flag_rule_violation_tool(rule_keys))
    config = snapshot.get("fantasy_mechanics")
    if (
        isinstance(config, dict)
        and type(config.get("version")) is int
        and config.get("version") == 1
        and config.get("profile") == "zegaris"
    ):
        declarations.append(
            types.FunctionDeclaration(
                name="propose_retrieval_event",
                description="Propose a completed retrieval mission event only when the narrated action establishes it. The game checks the location, sequence and inventory. Never use this to award payment.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "event": types.Schema(
                            type=types.Type.STRING,
                            enum=["accept_retrieval", "recover_body", "cremate_body"],
                        ),
                    },
                    required=["event"],
                ),
            )
        )
    if len(declarations) == len(base_declarations):
        return MASTER_MODE_TOOLS
    return types.Tool(function_declarations=declarations)
