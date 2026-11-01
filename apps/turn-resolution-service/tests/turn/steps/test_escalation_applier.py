"""Unit tests for escalation_applier.py."""

from app.models.tool_call import MasterModeTurnResult, ToolCallLogEntry
from app.turn.steps import escalation_applier

SNAPSHOT = {"state_schema": {"sanity": {"type": "number", "min": 0}}}


def _model_sanity_entry(delta: int = -2) -> ToolCallLogEntry:
    return ToolCallLogEntry(
        tool_name="adjust_numeric_field",
        arguments={"path": "sanity", "delta": delta},
        result={"success": True},
        is_valid=True,
    )


def _sink(*, is_marked: bool, sanity: int = 16) -> MasterModeTurnResult:
    return MasterModeTurnResult(
        final_state={"sanity": sanity},
        mutated_paths=["sanity"],
        tool_calls=[_model_sanity_entry(-4)],
        is_escalation_marked=is_marked,
    )


def test_marked_turn_costs_exactly_the_escalation_cost() -> None:
    sink = _sink(is_marked=True, sanity=16)

    escalation_applier.apply_escalation({"sanity": 20}, SNAPSHOT, sink)

    assert sink.final_state["sanity"] == 18
    assert sink.mutated_paths == ["sanity"]


def test_model_sanity_calls_are_marked_superseded() -> None:
    sink = _sink(is_marked=True)

    escalation_applier.apply_escalation({"sanity": 20}, SNAPSHOT, sink)

    assert sink.tool_calls[0].is_valid is False
    assert sink.tool_calls[0].result == escalation_applier.SUPERSEDED_RESULT


def test_unmarked_turn_is_untouched() -> None:
    sink = _sink(is_marked=False, sanity=16)

    escalation_applier.apply_escalation({"sanity": 20}, SNAPSHOT, sink)

    assert sink.final_state["sanity"] == 16
    assert sink.tool_calls[0].is_valid is True


def test_sanity_is_clamped_to_the_schema_minimum() -> None:
    sink = _sink(is_marked=True, sanity=0)

    escalation_applier.apply_escalation({"sanity": 1}, SNAPSHOT, sink)

    assert sink.final_state["sanity"] == 0


def test_missing_baseline_leaves_state_alone() -> None:
    sink = _sink(is_marked=True, sanity=16)

    escalation_applier.apply_escalation({}, SNAPSHOT, sink)

    assert sink.final_state["sanity"] == 16
