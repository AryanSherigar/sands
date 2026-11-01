"""Pydantic shapes for master-mode Gemini tool calls and validation results."""

from app.models.token_usage import TokenUsage
from pydantic import BaseModel, Field

MUTATION_TOOL_NAMES = frozenset(
    {"set_field", "adjust_numeric_field", "add_inventory_item"}
)


class ProposedMutation(BaseModel):
    """A single proposed state change, translated from a Gemini function call
    by tool_handler.py — not yet validated against schema or invariants."""

    tool_name: str
    op: str  # "set" | "increment" | "add_item" | "unknown"
    path: str | None = None
    value: object = None
    delta: int | float | None = None


class ProposedCheck(BaseModel):
    """A check the model flagged as warranted via propose_check — never
    resolves or mutates anything itself; see check_result_resolver.py."""

    check_type: str
    difficulty_class: int
    reasoning: str | None = None


class ValidationResult(BaseModel):
    """Outcome of state_validator.validate_mutation()/validate_applied_change()."""

    is_valid: bool
    updated_state: dict[str, object] | None = None
    error_message: str | None = None


class ToolCallLogEntry(BaseModel):
    """One tool call's record, persisted onto TurnLog.tool_calls."""

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)
    is_valid: bool


class MasterModeTurnResult(BaseModel):
    """Mutable sink ai_orchestrator.generate_narration() populates while
    streaming; read by pipeline.py/state_writer.py after the narration
    generator is exhausted (a generator's body has fully run by the time an
    `async for` over it completes, so this is a safe hand-off pattern)."""

    final_state: dict[str, object] = Field(default_factory=dict)
    mutated_paths: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallLogEntry] = Field(default_factory=list)
    proposed_check: ProposedCheck | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    is_escalation_marked: bool = False
    movement_destination_id: str | None = None
