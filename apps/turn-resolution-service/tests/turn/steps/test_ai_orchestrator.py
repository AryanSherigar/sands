"""Unit tests for ai_orchestrator.py, with the narration router mocked."""

import uuid

import pytest
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmUnavailableError,
    NarrationGenerationError,
)
from app.models.memory import (
    MemoryContext,
    MemoryItem,
    RetrieveResponse,
    Watermarks,
)
from app.models.token_usage import TokenUsage
from app.models.tool_call import MasterModeTurnResult
from app.models.turn import LoadedState, RecentTurn, TurnContext, TurnRequest
from app.turn import context_assembly
from app.turn.steps import ai_orchestrator
from google.genai import types


def _narration_chunks(events: list[tuple[str, str]]) -> list[str]:
    """Client-facing narration text only -- excludes narration_raw, the
    speaker-tag-annotated text ai_orchestrator also yields for the
    narration-audio step (app/turn/speaker_tags.py)."""
    return [data for event_type, data in events if event_type == "narration"]


def _turn_request(action_mode: str = "do") -> TurnRequest:
    return TurnRequest(
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        client_action_id=uuid.uuid4(),
        action_text="I draw my sword.",
        action_mode=action_mode,
        turn_count=0,
    )


def _loaded_state() -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "narrator_persona": "A grim voice.",
            "world_data": "A dungeon.",
        },
        state={"narrative": {}},
        turn_count=0,
        checkpoint=None,
    )


def _memory_response(items: list[MemoryItem]) -> RetrieveResponse:
    return RetrieveResponse(
        items=items,
        active_entities=[],
        scene=None,
        watermarks=Watermarks(
            ingested_seq=0, indexed_seq=0, extracted_seq=0, latest_seq_seen=0
        ),
        embedding_model="test-embedding",
    )


def _memory_item(text: str) -> MemoryItem:
    return MemoryItem(
        kind="fact",
        item_id=uuid.uuid4(),
        source_kind="fact",
        authority="authored",
        assertion="occurred",
        sequence=0,
        speaker=None,
        text=text,
        entity_ids=[],
    )


def _abstained_context() -> TurnContext:
    return TurnContext()


def _context_with_facts() -> TurnContext:
    return TurnContext(
        memory=MemoryContext(
            response=_memory_response([_memory_item("the door is locked")])
        )
    )


async def test_generate_narration_yields_all_chunks(monkeypatch) -> None:
    calls = []

    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        calls.append((system_instruction, prompt))
        for chunk in ["Hello, ", "adventurer."]:
            yield chunk

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        )
    ]

    assert "".join(_narration_chunks(events)) == "Hello, adventurer."
    system_instruction, prompt = calls[0]
    assert "A grim voice." in system_instruction
    assert system_instruction.startswith(
        "You are the narrator of an interactive story."
    )
    assert "Dungeon Master" not in system_instruction
    assert "A grim voice." not in prompt


async def test_generate_narration_retries_then_succeeds(monkeypatch) -> None:
    attempts = {"count": 0}

    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise LlmUnavailableError("simulated transient failure")
        yield "Recovered narration."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        )
    ]

    assert _narration_chunks(events) == ["Recovered narration."]
    assert attempts["count"] == 2


async def test_generate_narration_raises_after_retries_exhausted(monkeypatch) -> None:
    async def always_unavailable(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        raise LlmUnavailableError("simulated transient failure")
        yield  # pragma: no cover - unreachable, keeps this an async generator

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", always_unavailable
    )

    chunks = []
    with pytest.raises(NarrationGenerationError):
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        ):
            chunks.append(chunk)

    assert chunks == [ai_orchestrator._DEGRADED_NARRATION_MESSAGE]


async def test_generate_narration_content_blocked_degrades_without_retry(
    monkeypatch,
) -> None:
    attempts = {"count": 0}

    async def always_blocked(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        attempts["count"] += 1
        raise LlmContentBlockedError("simulated safety block")
        yield  # pragma: no cover - unreachable, keeps this an async generator

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", always_blocked
    )

    chunks = []
    with pytest.raises(NarrationGenerationError):
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        ):
            chunks.append(chunk)

    assert chunks == [ai_orchestrator._CONTENT_BLOCKED_NARRATION_MESSAGE]
    assert attempts["count"] == 1


async def test_generate_narration_prompt_includes_recalled_memory(monkeypatch) -> None:
    calls = []

    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        calls.append(prompt)
        yield "Narration."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    [
        chunk
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _context_with_facts()
        )
    ]

    assert "## Story Memory" in calls[0]
    assert "[lore] the door is locked" in calls[0]


async def test_generate_narration_prompt_omits_memory_block_without_items(
    monkeypatch,
) -> None:
    calls = []

    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        calls.append(prompt)
        yield "Narration."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    [
        chunk
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        )
    ]

    assert "## Story Memory" not in calls[0]


# --- Master mode: single-call native function-calling ----------------------


class _FakeResponse:
    """Duck-types the two GenerateContentResponse attributes ai_orchestrator
    actually reads per chunk: function_calls and text."""

    def __init__(
        self, function_calls: list[types.FunctionCall], text: str | None
    ) -> None:
        self.function_calls = function_calls
        self.text = text


def _master_loaded_state() -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "mode": "master",
            "narrator_persona": "Dry humor.",
            "world_data": {},
            "state_schema": {
                "flags": {
                    "type": "object",
                    "fields": {
                        "investigated_lore": {"type": "boolean", "initial": False}
                    },
                }
            },
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": [],
        },
        state={
            "flags": {"investigated_lore": False},
            "narrative": {},
        },
        turn_count=0,
        checkpoint=None,
    )


def _fake_stream(*responses: _FakeResponse):
    """Builds a stream_with_tools fake yielding the given chunks in order —
    mirrors the real shape (a function-call chunk carries no text)."""

    async def _generate(
        system_instruction: object,
        contents: object,
        timeout_seconds: object,
        tools: object,
        usage_sink: object = None,
    ):
        for response in responses:
            yield response

    return _generate


async def test_generate_narration_master_mode_single_call_applies_mutation_and_narrates(
    monkeypatch,
) -> None:
    """One tool call plus narration text, both from a single streamed call —
    no round trip needed since nothing depends on seeing a prior result."""
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse(
                [
                    types.FunctionCall(
                        name="set_field",
                        args={"path": "flags.investigated_lore", "value": "true"},
                    )
                ],
                None,
            ),
            _FakeResponse([], "You find a clue."),
        ),
    )

    result_sink = MasterModeTurnResult(
        final_state={
            "flags": {"investigated_lore": False},
            "narrative": {},
        }
    )
    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(),
            _master_loaded_state(),
            _abstained_context(),
            [],
            result_sink,
        )
    ]

    assert "".join(_narration_chunks(events)).strip() == "You find a clue."
    assert [tc.tool_name for tc in result_sink.tool_calls] == ["set_field"]
    assert result_sink.tool_calls[0].is_valid is True
    assert result_sink.final_state["flags"]["investigated_lore"] is True
    assert result_sink.mutated_paths == ["flags.investigated_lore"]


async def test_generate_narration_master_mode_captures_proposed_check(
    monkeypatch,
) -> None:
    """propose_check never touches state_validator/working_state — it's
    only recorded on result_sink for pipeline.py to stamp _pending_check."""
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse([], "The lock looks tricky. This calls for finesse."),
            _FakeResponse(
                [
                    types.FunctionCall(
                        name="propose_check",
                        args={
                            "check_type": "lockpicking",
                            "difficulty_class": 15,
                            "reasoning": "The mechanism is old and delicate.",
                        },
                    )
                ],
                None,
            ),
        ),
    )

    result_sink = MasterModeTurnResult(
        final_state={
            "flags": {"investigated_lore": False},
            "narrative": {},
        }
    )
    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(),
            _master_loaded_state(),
            _abstained_context(),
            [],
            result_sink,
        )
    ]

    assert "This calls for finesse." in "".join(_narration_chunks(events))
    assert result_sink.proposed_check is not None
    assert result_sink.proposed_check.check_type == "lockpicking"
    assert result_sink.proposed_check.difficulty_class == 15
    assert result_sink.mutated_paths == []
    assert result_sink.final_state["flags"]["investigated_lore"] is False


async def test_generate_narration_master_mode_rejects_invalid_mutation(
    monkeypatch,
) -> None:
    """There is no round trip: a rejected mutation is logged as invalid, and
    the narration from the same call still streams regardless."""
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse(
                [types.FunctionCall(name="unknown_tool", args={"foo": "bar"})], None
            ),
            _FakeResponse([], "Recovery."),
        ),
    )

    result_sink = MasterModeTurnResult(
        final_state={
            "flags": {"investigated_lore": False},
            "narrative": {},
        }
    )
    [
        chunk
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(),
            _master_loaded_state(),
            _abstained_context(),
            [],
            result_sink,
        )
    ]

    assert result_sink.tool_calls[0].is_valid is False
    assert result_sink.final_state["flags"]["investigated_lore"] is False
    assert result_sink.mutated_paths == []


async def test_generate_narration_master_mode_includes_active_instructions_and_persona(
    monkeypatch,
) -> None:
    captured = {}

    async def fake_stream_with_tools(
        system_instruction: object,
        contents: object,
        timeout_seconds: object,
        tools: object,
        usage_sink: object = None,
    ):
        captured["system_instruction"] = system_instruction
        captured["prompt"] = contents[0].parts[0].text
        yield _FakeResponse([], "Narration.")

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", fake_stream_with_tools
    )

    result_sink = MasterModeTurnResult(final_state={"narrative": {}})
    [
        chunk
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(),
            _master_loaded_state(),
            _abstained_context(),
            ["Kestrel Vane now travels with the player."],
            result_sink,
        )
    ]

    assert "Kestrel Vane now travels with the player." in captured["prompt"]
    assert "Kestrel Vane now travels" not in captured["system_instruction"]
    assert "Dry humor." in captured["system_instruction"]


async def test_generate_narration_emits_mood_and_clean_narration(monkeypatch) -> None:
    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        yield "[MOOD: tension]\n"
        yield "You hear distant footsteps echoing."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), _loaded_state(), _abstained_context()
        )
    ]

    assert events == [
        ("mood", "tension"),
        ("narration_raw", "You hear distant footsteps echoing."),
        ("narration", "You hear distant footsteps echoing."),
    ]


async def test_prompt_formats_history_as_dialogue_script(monkeypatch) -> None:
    calls = []

    async def fake_stream(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        calls.append(prompt)
        yield "Narration."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    state_with_history = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={"world_data": {"mainConflict": "The watch is corrupt."}},
        state={"narrative": {}},
        turn_count=1,
        checkpoint=None,
    )
    context = TurnContext(
        recent_turns=[
            RecentTurn(
                turn_number=1,
                participant_id=uuid.uuid4(),
                action_mode="do",
                action_text="I search the bushes.",
                narration_text="You find a hidden dagger.",
            )
        ]
    )

    [
        chunk
        async for _event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(), state_with_history, context
        )
    ]

    prompt = calls[0]
    assert "- Premise: The watch is corrupt." in prompt
    assert "## Recent Story Chronicle" in prompt
    assert "Player: I search the bushes." in prompt
    assert "Narrator: You find a hidden dagger." in prompt
    assert "## Current Player Action" in prompt
    assert "Player: I draw my sword." in prompt
    assert "{'action_text':" not in prompt


@pytest.mark.parametrize(
    "action_mode,expected_snippet",
    [
        ("say", "The player is speaking."),
        ("do", "The player is attempting a physical action."),
        ("story", "The player is requesting a narrative shift."),
    ],
)
def test_build_prompt_includes_action_mode_instruction(
    action_mode: str, expected_snippet: str
) -> None:
    prompt = context_assembly.assemble_prompt(
        _turn_request(action_mode), _loaded_state(), _abstained_context()
    )

    assert expected_snippet in prompt


def test_build_prompt_see_mode_has_no_action_instruction() -> None:
    prompt = context_assembly.assemble_prompt(
        _turn_request("see"), _loaded_state(), _abstained_context()
    )

    assert prompt.endswith("Player: I draw my sword.")


async def test_generate_narration_master_mode_emits_mood(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse(
                [],
                "[MOOD: combat]\nSteel clashes against steel with a deafening ring.",
            )
        ),
    )

    result_sink = MasterModeTurnResult(final_state={"flags": {}, "narrative": {}})
    events = [
        (event_type, chunk)
        async for event_type, chunk in ai_orchestrator.generate_narration(
            _turn_request(),
            _master_loaded_state(),
            _abstained_context(),
            [],
            result_sink,
        )
    ]

    assert events[0] == ("mood", "combat")
    narrations = [chunk for event_type, chunk in events if event_type == "narration"]
    full_narration = "".join(narrations)
    assert "[MOOD: combat]" not in full_narration
    assert "Steel clashes against steel" in full_narration


def _state_with_player_entity() -> tuple[LoadedState, TurnContext]:
    player_id = uuid.uuid4()
    loaded_state = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "world_data": "A kingdom.",
            "entities": [
                {
                    "entity_id": str(player_id),
                    "canonical_name": "Kaelen",
                    "aliases": ["The Wanderer"],
                    "is_player": True,
                    "description": "An exile.",
                }
            ],
            "rule_invariants": [],
        },
        state={
            "setup": {"character_name": "Kaelen", "class": "Spellblade"},
            "narrative": {},
        },
        turn_count=0,
        checkpoint=None,
    )
    context = TurnContext(
        memory=MemoryContext(
            response=_memory_response(
                [_memory_item("The Wanderer bears the Ancient Mark")]
            )
        )
    )
    return loaded_state, context


def test_player_character_prompt_and_memory_name_substitution() -> None:
    loaded_state, context = _state_with_player_entity()
    prompt = context_assembly.assemble_prompt(_turn_request(), loaded_state, context)
    assert "## Player Character (Protagonist)" in prompt
    assert "- Name: Kaelen (template archetype: The Wanderer)" in prompt
    assert "- Background: An exile." in prompt
    assert "- class: Spellblade" in prompt
    assert "Kaelen bears the Ancient Mark" in prompt
    assert "The Wanderer bears" not in prompt


def test_player_directive_in_master_system_instruction() -> None:
    loaded_state, _context = _state_with_player_entity()
    sys_instruction = ai_orchestrator._build_master_system_instruction(loaded_state)
    assert "Address the player character (Kaelen)" in sys_instruction


@pytest.mark.asyncio
async def test_generate_narration_records_token_usage_in_result_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MasterModeTurnResult()
    request = TurnRequest(
        client_action_id=uuid.uuid4(),
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        action_text="look around",
        action_mode="do",
        turn_count=1,
    )
    loaded = LoadedState(
        playthrough_id=request.playthrough_id,
        scenario_id=uuid.uuid4(),
        state={},
        scenario_snapshot={"mode": "master"},
        turn_count=1,
        checkpoint=None,
    )

    async def fake_stream_master(*args: object, **kwargs: object):
        usage = kwargs.get("usage_sink")
        if usage:
            usage.prompt_tokens = 200
            usage.completion_tokens = 80
            usage.model_name = "gemini-2.5-flash"

        yield _FakeResponse([], "Master narration")

    monkeypatch.setattr(
        ai_orchestrator, "_stream_master_mode_with_retries", fake_stream_master
    )

    events = [
        event
        async for event in ai_orchestrator.generate_narration(
            request, loaded, _abstained_context(), result_sink=sink
        )
    ]
    assert len(events) > 0
    assert sink.token_usage.prompt_tokens == 200
    assert sink.token_usage.completion_tokens == 80
    assert sink.token_usage.total_tokens == 280


@pytest.mark.asyncio
async def test_generate_narration_records_token_usage_in_newbie_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MasterModeTurnResult()
    request = _turn_request()
    loaded = _loaded_state()

    async def fake_stream_narration(
        system_instruction: str,
        prompt: str,
        timeout_seconds: int,
        usage_sink: object = None,
    ):
        if isinstance(usage_sink, TokenUsage):
            usage_sink.prompt_tokens = 150
            usage_sink.completion_tokens = 60
            usage_sink.model_name = "gemini-2.5-flash"
        yield "A calm tavern."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream_narration
    )

    events = [
        event
        async for event in ai_orchestrator.generate_narration(
            request, loaded, _abstained_context(), result_sink=sink
        )
    ]
    assert len(events) > 0
    assert sink.token_usage.prompt_tokens == 150
    assert sink.token_usage.completion_tokens == 60
    assert sink.token_usage.total_tokens == 210
    assert sink.token_usage.model_name == "gemini-2.5-flash"


def test_log_master_mode_completion_logs_token_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_info(event: str, **kwargs: object) -> None:
        captured["event"] = event
        captured.update(kwargs)

    monkeypatch.setattr(ai_orchestrator.logger, "info", fake_info)

    usage = TokenUsage(
        prompt_tokens=100, completion_tokens=50, model_name="gemini-2.5-flash"
    )
    ai_orchestrator._log_master_mode_completion(100.0, usage)

    assert captured["event"] == ai_orchestrator.EVENT_LLM_CALL_COMPLETED
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["prompt_tokens"] == 100
    assert captured["completion_tokens"] == 50
    assert captured["total_tokens"] == 150


def test_log_master_mode_completion_handles_none_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_info(event: str, **kwargs: object) -> None:
        captured["event"] = event
        captured.update(kwargs)

    monkeypatch.setattr(ai_orchestrator.logger, "info", fake_info)

    ai_orchestrator._log_master_mode_completion(100.0, None)

    assert captured["event"] == ai_orchestrator.EVENT_LLM_CALL_COMPLETED
    assert captured["prompt_tokens"] == 0
    assert captured["completion_tokens"] == 0
    assert captured["total_tokens"] == 0


def test_scenario_output_limit_is_read_from_the_snapshot() -> None:
    snapshot = {"narration_max_output_tokens": 1500}

    assert ai_orchestrator._narration_output_limit(snapshot) == 1500


def test_scenario_output_limit_is_clamped_to_the_ceiling(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "narration_max_output_tokens_ceiling", 2000)

    assert (
        ai_orchestrator._narration_output_limit({"narration_max_output_tokens": 9000})
        == 2000
    )


@pytest.mark.parametrize("value", [None, 0, -1, "1500", 1500.5, True])
def test_scenario_output_limit_ignores_unusable_values(value: object) -> None:
    snapshot = {"narration_max_output_tokens": value}

    assert ai_orchestrator._narration_output_limit(snapshot) is None
    assert ai_orchestrator._narration_output_limit({}) is None


def _capture_stream_kwargs(monkeypatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_stream_with_tools(*args: object, **kwargs: object):
        captured.update(kwargs)
        return iter(())

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", fake_stream_with_tools
    )
    return captured


def test_the_scenario_limit_reaches_the_provider_call(monkeypatch) -> None:
    captured = _capture_stream_kwargs(monkeypatch)

    ai_orchestrator._call_stream_with_tools("sys", [], 30, None, None, 1500)

    assert captured["max_output_tokens"] == 1500


def test_no_limit_leaves_the_provider_call_untouched(monkeypatch) -> None:
    captured = _capture_stream_kwargs(monkeypatch)

    ai_orchestrator._call_stream_with_tools("sys", [], 30, None, None)

    assert "max_output_tokens" not in captured


def _stream_events(stream: "ai_orchestrator._NarrationStream", chunks: list[str]):
    events: list[tuple[str, str]] = []
    for chunk in chunks:
        events.extend(stream.feed(chunk))
    events.extend(stream.finish())
    return events


_MOOD = "[MOOD: tension]\n"


def test_an_enabled_marker_is_hidden_from_the_player_and_collected() -> None:
    stream = ai_orchestrator._NarrationStream(is_intent_marker_enabled=True)
    chunks = [_MOOD, "[NARRATOR]\nRitsu nods.\n\n", "[INTENT: recruit_target=ritsu]"]

    events = _stream_events(stream, chunks)

    shown = "".join(data for kind, data in events if kind == "narration")
    raw = "".join(data for kind, data in events if kind == "narration_raw")
    assert "INTENT" not in shown and "INTENT" not in raw
    assert "Ritsu nods." in shown
    assert stream.intent_pairs == [("recruit_target", "ritsu")]


def test_a_disabled_marker_is_left_in_the_text() -> None:
    stream = ai_orchestrator._NarrationStream()

    events = _stream_events(stream, [_MOOD, "Text.\n\n[INTENT: a=b]"])

    assert "INTENT" in "".join(d for k, d in events if k == "narration")
    assert stream.intent_pairs == []


def test_a_marker_split_across_chunks_is_still_caught() -> None:
    stream = ai_orchestrator._NarrationStream(is_intent_marker_enabled=True)

    events = _stream_events(
        stream, [_MOOD, "Fine.\n\n[INT", "ENT: adopt_pol", "icy=tax_relief]"]
    )

    assert "INTENT" not in "".join(d for _, d in events)
    assert stream.intent_pairs == [("adopt_policy", "tax_relief")]


def test_the_group_is_read_from_the_snapshot() -> None:
    assert ai_orchestrator._intent_marker_group({"intent_marker_group": "intent"}) == (
        "intent"
    )
    assert ai_orchestrator._intent_marker_group({}) is None
    assert ai_orchestrator._intent_marker_group({"intent_marker_group": 3}) is None
