"""Test-only TRS entrypoint for the Night Desk end-to-end runs.

Serves the real application with the narrator replaced by a scripted one and the
memory service stubbed, so a run needs no Muse credentials and no memory stack.
The driver queues the next narrator response (text and optional tool calls) over
POST /__e2e/queue before each turn; an empty queue falls back to a plain line.
Every prompt the narrator would have received is served at GET /__e2e/prompts.
Never used outside docker-compose.e2e.night-desk.yml.
"""

from collections.abc import AsyncIterator

import uvicorn
from app.integrations import memory_client, narration_router
from app.main import app
from app.models.memory import RetrieveResponse, Watermarks
from app.turn.steps import memory_delivery
from google.genai import types
from pydantic import BaseModel, Field

DEFAULT_NARRATION = "The floor holds still."

_queue: list[dict[str, object]] = []
_recorded_prompts: list[str] = []


class _Chunk:
    def __init__(self, text: str | None, calls: list[types.FunctionCall]) -> None:
        self.text = text
        self.function_calls = calls
        self.candidates: list[object] = []


class ScriptedToolCall(BaseModel):
    name: str
    args: dict[str, object] = Field(default_factory=dict)


class QueuedResponse(BaseModel):
    narration: str = DEFAULT_NARRATION
    tool_calls: list[ScriptedToolCall] = Field(default_factory=list)


def _next_response() -> QueuedResponse:
    if _queue:
        return QueuedResponse.model_validate(_queue.pop(0))
    return QueuedResponse()


async def _scripted_stream_with_tools(
    system_instruction: str,
    contents: object,
    timeout_seconds: int,
    tools: object,
    usage_sink: object | None = None,
) -> AsyncIterator[_Chunk]:
    _recorded_prompts.append(str(system_instruction) + str(contents))
    response = _next_response()
    calls = [
        types.FunctionCall(name=call.name, args=call.args)
        for call in response.tool_calls
    ]
    if calls:
        yield _Chunk(None, calls)
    yield _Chunk(response.narration, [])


async def _empty_retrieve(request: object) -> RetrieveResponse:
    return RetrieveResponse(
        items=[],
        active_entities=[],
        scene=None,
        watermarks=Watermarks(
            ingested_seq=0, indexed_seq=0, extracted_seq=0, latest_seq_seen=0
        ),
        embedding_model="e2e-stub",
    )


async def _no_delivery(playthrough_id: object) -> None:
    return None


@app.post("/__e2e/queue")
async def queue_responses(responses: list[QueuedResponse]) -> dict[str, int]:
    _queue.extend(response.model_dump() for response in responses)
    return {"queued": len(_queue)}


@app.post("/__e2e/reset")
async def reset() -> dict[str, int]:
    _queue.clear()
    _recorded_prompts.clear()
    return {"queued": 0}


@app.get("/__e2e/prompts")
async def recorded_prompts() -> list[str]:
    return _recorded_prompts


narration_router.stream_with_tools = _scripted_stream_with_tools
memory_client.retrieve = _empty_retrieve
memory_delivery.deliver_after_commit = _no_delivery

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
