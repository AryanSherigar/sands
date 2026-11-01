"""Unit tests for narration_router.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.integrations import (
    anthropic_client,
    narration_router,
    openai_compatible_client,
)
from app.models.token_usage import TokenUsage
from google.genai import types


async def _dummy_stream(*args: object, **kwargs: object):
    yield "test-chunk"


async def test_stream_narration_routes_to_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(narration_router.settings, "narration_provider", "openai")
    mock_stream = MagicMock(side_effect=_dummy_stream)
    monkeypatch.setattr(openai_compatible_client, "stream_narration", mock_stream)

    sink = TokenUsage()
    chunks = [
        c
        async for c in narration_router.stream_narration(
            "instruction", "prompt", 10, usage_sink=sink
        )
    ]

    assert chunks == ["test-chunk"]
    mock_stream.assert_called_once_with("instruction", "prompt", 10, usage_sink=sink)


async def test_stream_chat_routes_to_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(narration_router.settings, "narration_provider", "openai")
    mock_stream = MagicMock(side_effect=_dummy_stream)
    monkeypatch.setattr(openai_compatible_client, "stream_chat", mock_stream)

    sink = TokenUsage()
    chunks = [
        c
        async for c in narration_router.stream_chat(
            "instruction", [], 10, max_output_tokens=500, usage_sink=sink
        )
    ]

    assert chunks == ["test-chunk"]
    mock_stream.assert_called_once_with("instruction", [], 10, 500, usage_sink=sink)


async def test_stream_narration_routes_to_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(narration_router.settings, "narration_provider", "anthropic")
    mock_stream = MagicMock(side_effect=_dummy_stream)
    monkeypatch.setattr(anthropic_client, "stream_narration", mock_stream)

    sink = TokenUsage()
    chunks = [
        c
        async for c in narration_router.stream_narration(
            "instruction", "prompt", 10, usage_sink=sink
        )
    ]

    assert chunks == ["test-chunk"]
    mock_stream.assert_called_once_with("instruction", "prompt", 10, usage_sink=sink)


async def test_stream_with_tools_routes_to_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(narration_router.settings, "narration_provider", "anthropic")
    mock_stream = MagicMock(side_effect=_dummy_stream)
    monkeypatch.setattr(anthropic_client, "stream_with_tools", mock_stream)

    contents = [types.Content(role="user", parts=[types.Part(text="hi")])]
    chunks = [
        c
        async for c in narration_router.stream_with_tools(
            "instruction", contents, 10, None
        )
    ]

    assert chunks == ["test-chunk"]
    mock_stream.assert_called_once()


async def test_stream_chat_stays_on_openai_compatible_when_provider_is_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(narration_router.settings, "narration_provider", "anthropic")
    mock_stream = MagicMock(side_effect=_dummy_stream)
    monkeypatch.setattr(openai_compatible_client, "stream_chat", mock_stream)

    chunks = [c async for c in narration_router.stream_chat("instruction", [], 10)]

    assert chunks == ["test-chunk"]
    mock_stream.assert_called_once()


def _call_response(*names: str) -> types.GenerateContentResponse:
    parts = [
        types.Part(function_call=types.FunctionCall(name=name, args={}))
        for name in names
    ]
    content = types.Content(role="model", parts=parts or [types.Part(text="")])
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content)])


def _install_openai_two_call(
    monkeypatch: pytest.MonkeyPatch, texts: list[str], response: object
) -> tuple[MagicMock, AsyncMock]:
    async def fake_chat(*args: object, **kwargs: object):
        usage_sink = kwargs.get("usage_sink")
        if usage_sink is not None:
            usage_sink.prompt_tokens = 100
            usage_sink.completion_tokens = 40
            usage_sink.model_name = "muse"
        for text in texts:
            yield text

    async def fake_generate(*args: object, **kwargs: object):
        usage_sink = kwargs.get("usage_sink")
        if usage_sink is not None:
            usage_sink.prompt_tokens = 150
            usage_sink.completion_tokens = 10
            usage_sink.model_name = "muse"
        return response

    chat = MagicMock(side_effect=fake_chat)
    generate = AsyncMock(side_effect=fake_generate)
    monkeypatch.setattr(narration_router.settings, "narration_provider", "openai")
    monkeypatch.setattr(openai_compatible_client, "stream_chat", chat)
    monkeypatch.setattr(openai_compatible_client, "generate_with_tools", generate)
    return chat, generate


async def test_openai_master_mode_streams_narration_then_records_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat, generate = _install_openai_two_call(
        monkeypatch, ["You pocket ", "the key."], _call_response("add_inventory_item")
    )
    tools = [types.Tool(function_declarations=[])]

    chunks = [c async for c in narration_router.stream_with_tools("sys", [], 10, tools)]

    assert [c.text for c in chunks[:2]] == ["You pocket ", "the key."]
    assert chunks[2].function_calls[0].name == "add_inventory_item"
    assert generate.await_args.args[3] == tools
    recorded = generate.await_args.args[1]
    assert recorded[-2].parts[0].text == "You pocket the key."
    assert recorded[-2].role == "model"
    assert recorded[-1].role == "user"
    chat.assert_called_once()


async def test_openai_master_mode_without_tools_makes_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _chat, generate = _install_openai_two_call(
        monkeypatch, ["Only prose."], _call_response()
    )

    chunks = [c async for c in narration_router.stream_with_tools("sys", [], 10, None)]

    assert [c.text for c in chunks] == ["Only prose."]
    generate.assert_not_awaited()


async def test_openai_master_mode_without_calls_yields_no_call_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_openai_two_call(monkeypatch, ["Quiet turn."], _call_response())
    tools = [types.Tool(function_declarations=[])]

    chunks = [c async for c in narration_router.stream_with_tools("sys", [], 10, tools)]

    assert len(chunks) == 1
    assert chunks[0].text == "Quiet turn."


async def test_openai_master_mode_sums_usage_across_both_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_openai_two_call(monkeypatch, ["Prose."], _call_response("set_field"))
    tools = [types.Tool(function_declarations=[])]
    sink = TokenUsage()

    _ = [
        c
        async for c in narration_router.stream_with_tools(
            "sys", [], 10, tools, usage_sink=sink
        )
    ]

    assert sink.prompt_tokens == 250
    assert sink.completion_tokens == 50
    assert sink.model_name == "muse"
