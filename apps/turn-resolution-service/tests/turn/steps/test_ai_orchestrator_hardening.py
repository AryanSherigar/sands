"""Empty-narration repair and escalation-marker tests for ai_orchestrator.py."""

import uuid

from app.models.tool_call import MasterModeTurnResult
from app.models.turn import LoadedState, TurnContext, TurnRequest
from app.turn.steps import ai_orchestrator
from google.genai import types

FALLBACK_LINE = "The desk lamp hums and nothing else answers."
ESCALATION_REPLY = "Acknowledged."
SANITY_CALL = types.FunctionCall(
    name="adjust_numeric_field", args={"path": "sanity", "delta": -2}
)


class _Chunk:
    def __init__(
        self, text: str | None, function_calls: list[types.FunctionCall] | None = None
    ) -> None:
        self.text = text
        self.function_calls = function_calls or []


def _scripted_calls(*calls: list[_Chunk]) -> tuple[object, list[object]]:
    """A stream_with_tools fake that plays one chunk list per call and records
    the tools argument of each call."""
    seen_tools: list[object] = []
    remaining = list(calls)

    async def _generate(
        system_instruction: object,
        contents: object,
        timeout_seconds: object,
        tools: object,
        usage_sink: object = None,
    ):
        seen_tools.append(tools)
        for chunk in remaining.pop(0):
            yield chunk

    return _generate, seen_tools


def _loaded_state(world_data: dict[str, str] | None = None) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "mode": "master",
            "narrator_persona": "Dry.",
            "world_data": world_data or {},
            "state_schema": {"sanity": {"type": "number", "initial": 20, "min": 0}},
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": [],
        },
        state={"sanity": 20, "narrative": {}},
        turn_count=0,
        checkpoint=None,
    )


def _request() -> TurnRequest:
    return TurnRequest(
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        client_action_id=uuid.uuid4(),
        action_text="I shout for help.",
        action_mode="do",
        turn_count=0,
    )


async def _run(
    monkeypatch, calls: list[list[_Chunk]], world_data: dict[str, str] | None = None
) -> tuple[list[tuple[str, str]], MasterModeTurnResult, list[object]]:
    generate, seen_tools = _scripted_calls(*calls)
    monkeypatch.setattr(ai_orchestrator.narration_router, "stream_with_tools", generate)
    sink = MasterModeTurnResult(final_state={"sanity": 20, "narrative": {}})
    events = [
        event
        async for event in ai_orchestrator.generate_narration(
            _request(), _loaded_state(world_data), TurnContext(), [], sink
        )
    ]
    return events, sink, seen_tools


def _narration(events: list[tuple[str, str]]) -> str:
    return "".join(data for kind, data in events if kind == "narration")


async def test_tool_calls_without_text_trigger_one_text_only_retry(monkeypatch) -> None:
    events, sink, seen_tools = await _run(
        monkeypatch,
        [[_Chunk(None, [SANITY_CALL])], [_Chunk("[NARRATOR]\nThe line goes dead.")]],
    )

    assert "The line goes dead." in _narration(events)
    assert len(seen_tools) == 2
    assert seen_tools[0] and seen_tools[1] is None
    assert [tc.tool_name for tc in sink.tool_calls] == ["adjust_numeric_field"]
    assert sink.final_state["sanity"] == 18


async def test_still_empty_after_retry_emits_scenario_fallback(monkeypatch) -> None:
    events, _, seen_tools = await _run(
        monkeypatch,
        [[_Chunk(None)], [_Chunk("   ")]],
        {"fallback_narration": FALLBACK_LINE},
    )

    assert _narration(events) == FALLBACK_LINE
    assert len(seen_tools) == 2


async def test_engine_default_fallback_when_scenario_has_none(monkeypatch) -> None:
    events, _, _ = await _run(monkeypatch, [[_Chunk(None)], [_Chunk(None)]])

    assert _narration(events) == ai_orchestrator._DEFAULT_FALLBACK_NARRATION


async def test_non_empty_first_attempt_is_not_retried(monkeypatch) -> None:
    events, _, seen_tools = await _run(monkeypatch, [[_Chunk("Fine prose.")]])

    assert "Fine prose." in _narration(events)
    assert len(seen_tools) == 1


async def test_escalation_marker_is_stripped_and_flagged(monkeypatch) -> None:
    events, sink, _ = await _run(
        monkeypatch,
        [[_Chunk("[NARRATOR]\n[ESCALATION]\nYour shout rings out.\n\n")]],
    )

    narration = _narration(events)
    assert "ESCALATION" not in narration
    assert "Your shout rings out." in narration
    assert sink.is_escalation_marked is True


async def test_mood_line_before_escalation_marker_keeps_mood_and_hides_tags(
    monkeypatch,
) -> None:
    events, sink, _ = await _run(
        monkeypatch,
        [[_Chunk("[MOOD: tension]\n[ESCALATION]\n[NARRATOR]\nYour shout rings out.")]],
    )

    narration = _narration(events)
    assert ("mood", "tension") in events
    assert "MOOD" not in narration
    assert "ESCALATION" not in narration
    assert sink.is_escalation_marked is True


def test_escalation_rule_precedes_the_player_directive() -> None:
    loaded_state = _loaded_state({"escalation_reply": ESCALATION_REPLY})

    instruction = ai_orchestrator._build_master_system_instruction(loaded_state)

    assert "[ESCALATION]" in instruction
    assert "after the [MOOD: ...] line" in instruction


async def test_escalation_reply_is_appended_when_missing(monkeypatch) -> None:
    events, _, _ = await _run(
        monkeypatch,
        [[_Chunk("[ESCALATION]\n[NARRATOR]\nIt echoes.")]],
        {"escalation_reply": ESCALATION_REPLY},
    )

    assert _narration(events).rstrip().endswith(ESCALATION_REPLY)


async def test_escalation_reply_not_duplicated_when_present(monkeypatch) -> None:
    events, _, _ = await _run(
        monkeypatch,
        [[_Chunk("[ESCALATION]\n[NARRATOR]\nAcknowledged. It echoes.")]],
        {"escalation_reply": ESCALATION_REPLY},
    )

    assert _narration(events).count(ESCALATION_REPLY) == 1


async def test_no_marker_means_no_reply(monkeypatch) -> None:
    events, sink, _ = await _run(
        monkeypatch,
        [[_Chunk("[NARRATOR]\nQuiet.")]],
        {"escalation_reply": ESCALATION_REPLY},
    )

    assert ESCALATION_REPLY not in _narration(events)
    assert sink.is_escalation_marked is False


def test_escalation_rule_only_in_system_instruction_when_scenario_has_reply() -> None:
    without_rule = ai_orchestrator._build_master_system_instruction(_loaded_state())
    with_rule = ai_orchestrator._build_master_system_instruction(
        _loaded_state({"escalation_reply": ESCALATION_REPLY})
    )

    assert "[ESCALATION]" not in without_rule
    assert "[ESCALATION]" in with_rule
