"""Unit tests for openai_compatible_client.py.

All openai SDK calls are monkeypatched — no real network or API key needed.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmUnavailableError,
)
from app.integrations import openai_compatible_client
from app.models.token_usage import TokenUsage
from google.genai import types

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stream_chunk(
    content: str | None,
    usage: object | None = None,
    has_choice: bool = True,
) -> MagicMock:
    chunk = MagicMock()
    if has_choice:
        choice = MagicMock()
        choice.delta.content = content
        chunk.choices = [choice]
    else:
        chunk.choices = []
    chunk.usage = usage
    return chunk


def _make_completion(
    text: str | None = None,
    tool_calls: list[dict[str, object]] | None = None,
    usage: object | None = None,
) -> MagicMock:
    """Build a minimal ChatCompletion mock."""
    message = MagicMock()
    message.content = text
    if tool_calls:
        raw_calls = []
        for tc in tool_calls:
            call = MagicMock()
            call.id = tc["id"]
            call.function.name = tc["name"]
            call.function.arguments = json.dumps(tc["args"])
            raw_calls.append(call)
        message.tool_calls = raw_calls
    else:
        message.tool_calls = None
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message = message
    completion.usage = usage
    return completion


async def _fake_stream(chunks: list[MagicMock | Exception]):
    """Async generator that yields chunks or raises exceptions."""
    for item in chunks:
        if isinstance(item, Exception):
            raise item
        yield item


def _install_fake_async_client(monkeypatch, *, stream_chunks=None, completion=None):
    """Replace the cached _client with a minimal AsyncOpenAI stand-in."""
    fake_client = MagicMock()

    if stream_chunks is not None:
        fake_client.chat.completions.create = AsyncMock(
            return_value=_fake_stream(stream_chunks)
        )
    if completion is not None:
        fake_client.chat.completions.create = AsyncMock(return_value=completion)

    monkeypatch.setattr(openai_compatible_client, "_client", fake_client)
    return fake_client


# ---------------------------------------------------------------------------
# stream_narration tests
# ---------------------------------------------------------------------------


async def test_stream_narration_yields_delta_text(monkeypatch) -> None:
    _install_fake_async_client(
        monkeypatch,
        stream_chunks=[_make_stream_chunk("Hello, "), _make_stream_chunk("world.")],
    )

    chunks = [
        c async for c in openai_compatible_client.stream_narration("sys", "prompt", 5)
    ]

    assert chunks == ["Hello, ", "world."]


async def test_stream_narration_skips_empty_deltas(monkeypatch) -> None:
    _install_fake_async_client(
        monkeypatch,
        stream_chunks=[_make_stream_chunk(None), _make_stream_chunk("Only real text.")],
    )

    chunks = [
        c async for c in openai_compatible_client.stream_narration("sys", "prompt", 5)
    ]

    assert chunks == ["Only real text."]


async def test_stream_narration_timeout_raises_gemini_unavailable(monkeypatch) -> None:
    _install_fake_async_client(
        monkeypatch,
        stream_chunks=[openai.APITimeoutError(request=MagicMock())],
    )

    with pytest.raises(LlmUnavailableError):
        async for _ in openai_compatible_client.stream_narration("sys", "prompt", 5):
            pass


async def test_stream_narration_rate_limit_raises_gemini_unavailable(
    monkeypatch,
) -> None:
    _install_fake_async_client(
        monkeypatch,
        stream_chunks=[
            openai.RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        ],
    )

    with pytest.raises(LlmUnavailableError):
        async for _ in openai_compatible_client.stream_narration("sys", "prompt", 5):
            pass


async def test_stream_narration_bad_request_raises_content_blocked(
    monkeypatch,
) -> None:
    _install_fake_async_client(
        monkeypatch,
        stream_chunks=[
            openai.BadRequestError(
                message="content blocked",
                response=MagicMock(status_code=400),
                body=None,
            )
        ],
    )

    with pytest.raises(LlmContentBlockedError):
        async for _ in openai_compatible_client.stream_narration("sys", "prompt", 5):
            pass


# ---------------------------------------------------------------------------
# generate_with_tools tests
# ---------------------------------------------------------------------------


async def test_generate_with_tools_no_tool_calls_returns_text(monkeypatch) -> None:
    completion = _make_completion(text="The dragon roars.")
    _install_fake_async_client(monkeypatch, completion=completion)

    result = await openai_compatible_client.generate_with_tools(
        "sys", [], 5, tools=None
    )

    assert result.text == "The dragon roars."
    assert not result.function_calls


async def test_generate_with_tools_tool_call_translates_function_call(
    monkeypatch,
) -> None:
    completion = _make_completion(
        tool_calls=[
            {
                "id": "call_abc",
                "name": "set_field",
                "args": {"path": "hp", "value": "10"},
            }
        ]
    )
    _install_fake_async_client(monkeypatch, completion=completion)

    result = await openai_compatible_client.generate_with_tools(
        "sys", [], 5, tools=None
    )

    calls = result.function_calls
    assert calls and len(calls) == 1
    assert calls[0].name == "set_field"
    assert calls[0].args == {"path": "hp", "value": "10"}


# ---------------------------------------------------------------------------
# Schema translation tests (no network calls)
# ---------------------------------------------------------------------------


def test_gemini_tool_to_openai_schema() -> None:
    tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="set_field",
                description="Set a state field.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "path": types.Schema(type=types.Type.STRING),
                        "value": types.Schema(type=types.Type.STRING),
                    },
                    required=["path", "value"],
                ),
            )
        ]
    )

    result = openai_compatible_client._gemini_tools_to_openai([tool])

    assert len(result) == 1
    fn = result[0]
    assert fn["type"] == "function"
    func = fn["function"]
    assert func["name"] == "set_field"
    params = func["parameters"]
    assert params["type"] == "object"
    assert "path" in params["properties"]
    assert params["required"] == ["path", "value"]


def test_gemini_contents_to_openai_messages() -> None:
    contents = [
        types.Content(role="user", parts=[types.Part(text="Hello")]),
        types.Content(role="model", parts=[types.Part(text="Hi there")]),
    ]

    messages = openai_compatible_client._gemini_contents_to_openai_messages(
        "You are a narrator.", contents
    )

    assert messages[0] == {"role": "system", "content": "You are a narrator."}
    assert messages[1] == {"role": "user", "content": "Hello"}
    assert messages[2] == {"role": "assistant", "content": "Hi there"}


async def test_stream_narration_captures_token_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 40
    mock_usage.completion_tokens = 15

    chunk1 = _make_stream_chunk("Hello")
    chunk2 = _make_stream_chunk(None, usage=mock_usage, has_choice=False)
    _install_fake_async_client(monkeypatch, stream_chunks=[chunk1, chunk2])
    monkeypatch.setattr(
        openai_compatible_client.settings,
        "openai_compatible_model_name",
        "mock-openai-model",
    )

    sink = TokenUsage()
    chunks = [
        c
        async for c in openai_compatible_client.stream_narration(
            "sys", "prompt", 5, usage_sink=sink
        )
    ]

    assert chunks == ["Hello"]
    assert sink.prompt_tokens == 40
    assert sink.completion_tokens == 15
    assert sink.model_name == "mock-openai-model"


async def test_stream_chat_captures_token_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 60
    mock_usage.completion_tokens = 25

    chunk1 = _make_stream_chunk("Response")
    chunk2 = _make_stream_chunk(None, usage=mock_usage, has_choice=False)
    _install_fake_async_client(monkeypatch, stream_chunks=[chunk1, chunk2])
    monkeypatch.setattr(
        openai_compatible_client.settings,
        "openai_compatible_model_name",
        "mock-openai-model",
    )

    sink = TokenUsage()
    chunks = [
        c
        async for c in openai_compatible_client.stream_chat(
            "sys", [], 5, usage_sink=sink
        )
    ]

    assert chunks == ["Response"]
    assert sink.prompt_tokens == 60
    assert sink.completion_tokens == 25
    assert sink.model_name == "mock-openai-model"


async def test_generate_with_tools_captures_token_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 80
    mock_usage.completion_tokens = 30
    completion = _make_completion(text="The dragon roars.", usage=mock_usage)
    _install_fake_async_client(monkeypatch, completion=completion)
    monkeypatch.setattr(
        openai_compatible_client.settings,
        "openai_compatible_model_name",
        "mock-openai-model",
    )

    sink = TokenUsage()
    result = await openai_compatible_client.generate_with_tools(
        "sys", [], 5, tools=None, usage_sink=sink
    )

    assert result.text == "The dragon roars."
    assert sink.prompt_tokens == 80
    assert sink.completion_tokens == 30
    assert sink.model_name == "mock-openai-model"


async def test_reasoning_effort_is_sent_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_async_client(
        monkeypatch, stream_chunks=[_make_stream_chunk("Hi.")]
    )
    monkeypatch.setattr(
        openai_compatible_client.settings,
        "openai_compatible_reasoning_effort",
        "minimal",
    )

    _ = [c async for c in openai_compatible_client.stream_narration("sys", "go", 5)]

    sent = fake_client.chat.completions.create.call_args.kwargs
    assert sent["reasoning_effort"] == "minimal"


async def test_reasoning_effort_is_omitted_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completion = _make_completion(text="Done.")
    fake_client = _install_fake_async_client(monkeypatch, completion=completion)
    monkeypatch.setattr(
        openai_compatible_client.settings, "openai_compatible_reasoning_effort", ""
    )

    await openai_compatible_client.generate_with_tools("sys", [], 5, tools=None)

    sent = fake_client.chat.completions.create.call_args.kwargs
    assert "reasoning_effort" not in sent


async def test_stream_chat_sends_max_completion_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_async_client(
        monkeypatch, stream_chunks=[_make_stream_chunk("Hi.")]
    )

    _ = [c async for c in openai_compatible_client.stream_chat("sys", [], 5, 321)]

    sent = fake_client.chat.completions.create.call_args.kwargs
    assert sent["max_completion_tokens"] == 321
    assert "max_tokens" not in sent


async def test_generate_with_tools_keeps_narration_text_beside_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completion = _make_completion(
        text="You pocket the key.",
        tool_calls=[{"id": "call_1", "name": "set_field", "args": {"path": "a"}}],
    )
    _install_fake_async_client(monkeypatch, completion=completion)

    result = await openai_compatible_client.generate_with_tools(
        "sys", [], 5, tools=None
    )

    assert result.text == "You pocket the key."
    assert result.function_calls and result.function_calls[0].name == "set_field"


async def test_record_openai_usage_reads_cached_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 60
    mock_usage.completion_tokens = 25
    mock_usage.prompt_tokens_details.cached_tokens = 40
    chunks = [
        _make_stream_chunk("Response"),
        _make_stream_chunk(None, usage=mock_usage, has_choice=False),
    ]
    _install_fake_async_client(monkeypatch, stream_chunks=chunks)

    sink = TokenUsage()
    _ = [
        c
        async for c in openai_compatible_client.stream_chat(
            "sys", [], 5, usage_sink=sink
        )
    ]

    assert sink.cached_tokens == 40


async def test_record_openai_usage_leaves_cached_tokens_zero_without_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 60
    mock_usage.completion_tokens = 25
    mock_usage.prompt_tokens_details = None
    chunks = [
        _make_stream_chunk("Response"),
        _make_stream_chunk(None, usage=mock_usage, has_choice=False),
    ]
    _install_fake_async_client(monkeypatch, stream_chunks=chunks)

    sink = TokenUsage()
    _ = [
        c
        async for c in openai_compatible_client.stream_chat(
            "sys", [], 5, usage_sink=sink
        )
    ]

    assert sink.cached_tokens == 0


def _status_error(error_type: type[openai.APIStatusError], status_code: int):
    return error_type(
        message="rejected", response=MagicMock(status_code=status_code), body=None
    )


async def test_stream_chat_authentication_error_raises_llm_unavailable(
    monkeypatch,
) -> None:
    _install_fake_async_client(
        monkeypatch, stream_chunks=[_status_error(openai.AuthenticationError, 401)]
    )

    with pytest.raises(LlmUnavailableError):
        async for _ in openai_compatible_client.stream_chat("sys", [], 5):
            pass


async def test_stream_chat_server_error_raises_llm_unavailable(monkeypatch) -> None:
    _install_fake_async_client(
        monkeypatch, stream_chunks=[_status_error(openai.InternalServerError, 503)]
    )

    with pytest.raises(LlmUnavailableError):
        async for _ in openai_compatible_client.stream_chat("sys", [], 5):
            pass


async def test_stream_narration_server_error_raises_llm_unavailable(
    monkeypatch,
) -> None:
    _install_fake_async_client(
        monkeypatch, stream_chunks=[_status_error(openai.InternalServerError, 500)]
    )

    with pytest.raises(LlmUnavailableError):
        async for _ in openai_compatible_client.stream_narration("sys", "prompt", 5):
            pass


async def test_generate_with_tools_authentication_error_raises_llm_unavailable(
    monkeypatch,
) -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=_status_error(openai.AuthenticationError, 401)
    )
    monkeypatch.setattr(openai_compatible_client, "_client", fake_client)

    with pytest.raises(LlmUnavailableError):
        await openai_compatible_client.generate_with_tools("sys", [], 5, tools=None)
