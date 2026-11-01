"""Unit tests for anthropic_client.py, with the Vertex HTTP transport mocked."""

import json
from collections.abc import Callable

import httpx2
import pytest
from anthropic import AsyncAnthropicVertex
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmNotConfiguredError,
    LlmUnavailableError,
)
from app.integrations import anthropic_client
from app.models.token_usage import TokenUsage
from app.turn import tool_definitions
from google.genai import types

MODEL_NAME = "claude-haiku-5-5"


def _sse(events: list[dict[str, object]]) -> bytes:
    lines = [
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    ]
    return "".join(lines).encode()


def _message_start(
    input_tokens: int = 100, cache_read: int = 0, cache_write: int = 0
) -> dict[str, object]:
    return {
        "type": "message_start",
        "message": {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": MODEL_NAME,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
                "output_tokens": 1,
            },
        },
    }


def _text_block(index: int, *pieces: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "text", "text": ""},
        }
    ]
    for piece in pieces:
        events.append(
            {
                "type": "content_block_delta",
                "index": index,
                "delta": {"type": "text_delta", "text": piece},
            }
        )
    events.append({"type": "content_block_stop", "index": index})
    return events


def _tool_block(
    index: int, tool_id: str, name: str, *json_parts: str
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "tool_use",
                "id": tool_id,
                "name": name,
                "input": {},
            },
        }
    ]
    for part in json_parts:
        events.append(
            {
                "type": "content_block_delta",
                "index": index,
                "delta": {"type": "input_json_delta", "partial_json": part},
            }
        )
    events.append({"type": "content_block_stop", "index": index})
    return events


def _message_end(
    stop_reason: str = "end_turn", output_tokens: int = 42
) -> list[dict[str, object]]:
    return [
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        },
        {"type": "message_stop"},
    ]


class _Recorder:
    def __init__(self) -> None:
        self.bodies: list[dict[str, object]] = []


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> _Recorder:
    recorder = _Recorder()

    def recording_handler(request: httpx2.Request) -> httpx2.Response:
        recorder.bodies.append(json.loads(request.content))
        return handler(request)

    client = AsyncAnthropicVertex(
        region="global",
        project_id="test-project",
        access_token="test-token",
        http_client=httpx2.AsyncClient(
            transport=httpx2.MockTransport(recording_handler)
        ),
        max_retries=0,
    )
    monkeypatch.setattr(anthropic_client, "_client", client)
    return recorder


def _stream_response(events: list[dict[str, object]]) -> Callable[..., httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=_sse(events), headers={"content-type": "text/event-stream"}
        )

    return handler


def _error_response(status: int) -> Callable[..., httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = {"type": "error", "error": {"type": "api_error", "message": "boom"}}
        return httpx2.Response(status, json=body)

    return handler


def _user(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _tools() -> list[types.Tool]:
    schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING),
            "rule_id": types.Schema(type=types.Type.STRING, enum=["a", "b"]),
        },
        required=["path"],
    )
    declarations = [
        types.FunctionDeclaration(name="set_state", description="d", parameters=schema),
        types.FunctionDeclaration(name="other", description="o", parameters=schema),
    ]
    return [types.Tool(function_declarations=declarations)]


async def test_stream_narration_yields_text_and_records_usage(monkeypatch) -> None:
    events = [
        _message_start(input_tokens=20, cache_read=300, cache_write=50),
        *_text_block(0, "The door ", "creaks."),
        *_message_end(output_tokens=7),
    ]
    _install_transport(monkeypatch, _stream_response(events))
    usage = TokenUsage()

    chunks = [
        text
        async for text in anthropic_client.stream_narration(
            "system text", "player prompt", 10, usage_sink=usage
        )
    ]

    assert chunks == ["The door ", "creaks."]
    assert usage.prompt_tokens == 370
    assert usage.completion_tokens == 7
    assert usage.model_name == anthropic_client.settings.anthropic_model_name


async def test_request_body_omits_sampling_and_marks_cache_breakpoints(
    monkeypatch,
) -> None:
    events = [_message_start(), *_text_block(0, "ok"), *_message_end()]
    recorder = _install_transport(monkeypatch, _stream_response(events))

    chunks = [
        chunk
        async for chunk in anthropic_client.stream_with_tools(
            "system text", [_user("act")], 10, _tools()
        )
    ]

    assert chunks[0].text == "ok"
    body = recorder.bodies[0]
    for forbidden in ("temperature", "top_p", "top_k"):
        assert forbidden not in body
    assert body["system"] == [
        {"type": "text", "text": "system text", "cache_control": {"type": "ephemeral"}}
    ]
    assert body["output_config"] == {
        "effort": anthropic_client.settings.anthropic_effort
    }
    assert body["messages"][-1]["role"] == "user"
    assert body["tool_choice"] == {"type": "auto"}
    sent_tools = body["tools"]
    assert "cache_control" not in sent_tools[0]
    assert sent_tools[-1]["cache_control"] == {"type": "ephemeral"}
    assert sent_tools[0]["input_schema"]["properties"]["rule_id"]["enum"] == ["a", "b"]
    assert sent_tools[0]["input_schema"]["required"] == ["path"]


async def test_tool_call_split_across_deltas_arrives_as_one_function_call(
    monkeypatch,
) -> None:
    events = [
        _message_start(),
        *_text_block(0, "Narration."),
        *_tool_block(1, "toolu_1", "set_state", '{"path": "hp', '", "value": 3}'),
        *_message_end(stop_reason="tool_use"),
    ]
    _install_transport(monkeypatch, _stream_response(events))

    chunks = [
        chunk
        async for chunk in anthropic_client.stream_with_tools(
            "system", [_user("act")], 10, _tools()
        )
    ]

    assert [chunk.text for chunk in chunks[:1]] == ["Narration."]
    calls = chunks[1].function_calls
    assert len(calls) == 1
    assert calls[0].name == "set_state"
    assert calls[0].args == {"path": "hp", "value": 3}
    assert calls[0].id == "toolu_1"


async def test_parallel_tool_calls_are_separate_function_calls(monkeypatch) -> None:
    events = [
        _message_start(),
        *_tool_block(0, "toolu_1", "set_state", '{"path": "a"}'),
        *_tool_block(1, "toolu_2", "other", '{"path": "b"}'),
        *_message_end(stop_reason="tool_use"),
    ]
    _install_transport(monkeypatch, _stream_response(events))

    chunks = [
        chunk
        async for chunk in anthropic_client.stream_with_tools(
            "system", [_user("act")], 10, _tools()
        )
    ]

    names = [call.name for chunk in chunks for call in chunk.function_calls or []]
    assert names == ["set_state", "other"]


async def test_malformed_tool_input_becomes_empty_args(monkeypatch) -> None:
    events = [
        _message_start(),
        *_tool_block(0, "toolu_1", "set_state", '{"path": '),
        *_message_end(stop_reason="tool_use"),
    ]
    _install_transport(monkeypatch, _stream_response(events))

    chunks = [
        chunk
        async for chunk in anthropic_client.stream_with_tools(
            "system", [_user("act")], 10, _tools()
        )
    ]

    assert chunks[0].function_calls[0].args == {}


async def test_thinking_blocks_are_never_yielded_as_narration(monkeypatch) -> None:
    thinking = [
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "hidden"},
        },
        {"type": "content_block_stop", "index": 0},
    ]
    events = [_message_start(), *thinking, *_text_block(1, "Visible."), *_message_end()]
    _install_transport(monkeypatch, _stream_response(events))

    chunks = [
        text async for text in anthropic_client.stream_narration("system", "prompt", 10)
    ]

    assert chunks == ["Visible."]


async def test_refusal_maps_to_content_blocked(monkeypatch) -> None:
    events = [_message_start(), *_message_end(stop_reason="refusal")]
    _install_transport(monkeypatch, _stream_response(events))

    with pytest.raises(LlmContentBlockedError):
        [text async for text in anthropic_client.stream_narration("s", "p", 10)]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (429, LlmUnavailableError),
        (500, LlmUnavailableError),
        (529, LlmUnavailableError),
        (400, LlmContentBlockedError),
        (403, LlmContentBlockedError),
        (401, LlmNotConfiguredError),
        (404, LlmNotConfiguredError),
    ],
)
async def test_http_errors_map_to_domain_errors(
    monkeypatch, status: int, expected: type[Exception]
) -> None:
    _install_transport(monkeypatch, _error_response(status))

    with pytest.raises(expected):
        [text async for text in anthropic_client.stream_narration("s", "p", 10)]


async def test_model_role_maps_to_assistant_and_messages_end_with_user(
    monkeypatch,
) -> None:
    events = [_message_start(), *_text_block(0, "ok"), *_message_end()]
    recorder = _install_transport(monkeypatch, _stream_response(events))
    contents = [
        _user("first"),
        types.Content(role="model", parts=[types.Part(text="reply")]),
        _user("second"),
    ]

    [c async for c in anthropic_client.stream_with_tools("s", contents, 10, None)]

    roles = [message["role"] for message in recorder.bodies[0]["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert "tools" not in recorder.bodies[0]


def test_cached_prefix_is_identical_across_consecutive_turns() -> None:
    tools = [tool_definitions.build_master_mode_tools({})]
    first = anthropic_client._build_request("system text", [_user("turn one")], tools)
    second = anthropic_client._build_request("system text", [_user("turn two")], tools)

    for prefix_key in ("tools", "system", "model", "output_config"):
        assert json.dumps(first[prefix_key]) == json.dumps(second[prefix_key])
    assert first["messages"] != second["messages"]
    assert first["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert first["system"][-1]["cache_control"] == {"type": "ephemeral"}


def test_request_uses_the_scenario_output_limit_when_given() -> None:
    default = anthropic_client._build_request("system", [_user("hi")], None)
    scenario = anthropic_client._build_request("system", [_user("hi")], None, 1500)

    assert (
        default["max_tokens"] == anthropic_client.settings.anthropic_max_output_tokens
    )
    assert scenario["max_tokens"] == 1500
