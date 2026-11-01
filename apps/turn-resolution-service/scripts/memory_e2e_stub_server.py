"""Test-only TRS entrypoint for the memory end-to-end runs.

Serves the real application with the narrator replaced by a deterministic one,
so a run needs no Muse credentials and produces searchable text per turn. It
also records every prompt the narrator would have received and serves them at
GET /__e2e/prompts, so a run can assert on what the prompt contained. Never used
outside docker-compose.e2e.yml.
"""

import itertools
from collections.abc import AsyncIterator

import uvicorn
from app.integrations import narration_router
from app.main import app
from google.genai import types

NARRATION_MARKER = "zephyrine"
_turn_counter = itertools.count(1)
_tool_turn_counter = itertools.count(1)
_recorded_prompts: list[dict[str, str]] = []
PROPOSED_CHECK_TYPE = "lockpicking"
PROPOSED_CHECK_DIFFICULTY = 12


class _StubToolChunk:
    """What ai_orchestrator reads from a tool-calling stream chunk."""

    def __init__(self, text: str, function_calls: list[types.FunctionCall]) -> None:
        self.text = text
        self.function_calls = function_calls
        self.candidates: list[object] = []


async def _stub_stream_narration(
    system_instruction: str,
    prompt: str,
    timeout_seconds: int,
    usage_sink: object | None = None,
) -> AsyncIterator[str]:
    turn = next(_turn_counter)
    _recorded_prompts.append(
        {"system_instruction": system_instruction, "prompt": prompt}
    )
    yield f"Turn {turn}: the archivist whispers about the {NARRATION_MARKER} lantern. "
    yield f"Marker {turn} glows over Harrowmere."


async def _stub_stream_with_tools(
    system_instruction: str,
    contents: object,
    timeout_seconds: int,
    tools: object,
    usage_sink: object | None = None,
) -> AsyncIterator[_StubToolChunk]:
    """Master mode: the first call proposes a check, every later call only narrates."""
    call = next(_tool_turn_counter)
    function_calls: list[types.FunctionCall] = []
    if call == 1:
        function_calls.append(
            types.FunctionCall(
                name="propose_check",
                args={
                    "check_type": PROPOSED_CHECK_TYPE,
                    "difficulty_class": PROPOSED_CHECK_DIFFICULTY,
                    "reasoning": "The old lock resists.",
                },
            )
        )
    yield _StubToolChunk(
        f"Tool turn {call}: the warden watches the lock.", function_calls
    )


@app.get("/__e2e/prompts")
async def recorded_prompts() -> list[dict[str, str]]:
    return _recorded_prompts


narration_router.stream_narration = _stub_stream_narration
narration_router.stream_with_tools = _stub_stream_with_tools

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
