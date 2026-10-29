"""Claude narration client for Turn Resolution Service.

Calls Claude on Vertex AI (Messages API, Application Default Credentials) and
keeps the same public interface as gemini_client.py. It accepts and returns
google.genai types so `ai_orchestrator.py` and the tool handlers stay unchanged:
text streams token by token, and each tool_use block is emitted as one complete
FunctionCall chunk once its JSON input has fully arrived.

Configuration is read only from app.config.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

import anthropic
import structlog
from anthropic import AsyncAnthropicVertex
from anthropic.types import (
    InputJSONDelta,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStreamEvent,
    TextDelta,
    ToolUseBlock,
)
from app.config import settings
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmNotConfiguredError,
    LlmUnavailableError,
)
from app.models.token_usage import TokenUsage
from google.auth.exceptions import GoogleAuthError
from google.genai import types

logger = structlog.get_logger()

EVENT_ANTHROPIC_STREAM_OPENED = "anthropic_stream_opened"
EVENT_ANTHROPIC_STREAM_ERROR = "anthropic_stream_error"
EVENT_ANTHROPIC_STREAM_USAGE = "anthropic_stream_usage"

STOP_REASON_REFUSAL = "refusal"
HTTP_STATUS_SERVER_ERROR_MIN = 500
CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}

_client: AsyncAnthropicVertex | None = None


def _get_client() -> AsyncAnthropicVertex:
    """Build the Vertex client lazily so importing never needs credentials."""
    global _client
    if _client is None:
        _client = AsyncAnthropicVertex(
            region=settings.google_cloud_location,
            project_id=settings.google_cloud_project or anthropic.NOT_GIVEN,
            max_retries=0,
        )
    return _client


@contextmanager
def _translated_errors() -> Iterator[None]:
    try:
        yield
    except (asyncio.TimeoutError, anthropic.APITimeoutError) as exc:
        raise _unavailable("TimeoutError", exc) from exc
    except anthropic.APIConnectionError as exc:
        raise _unavailable("ConnectionError", exc) from exc
    except anthropic.RateLimitError as exc:
        raise _unavailable("RateLimitError", exc) from exc
    except anthropic.APIStatusError as exc:
        raise _from_status_error(exc) from exc
    except GoogleAuthError as exc:
        logger.error(EVENT_ANTHROPIC_STREAM_ERROR, error_type="AuthError")
        raise LlmNotConfiguredError() from exc


def _unavailable(error_type: str, exc: Exception) -> LlmUnavailableError:
    logger.warning(EVENT_ANTHROPIC_STREAM_ERROR, error_type=error_type)
    return LlmUnavailableError()


def _from_status_error(exc: anthropic.APIStatusError) -> Exception:
    status = exc.status_code
    if status >= HTTP_STATUS_SERVER_ERROR_MIN:
        return _unavailable("ServerError", exc)
    if status in (401, 404):
        logger.error(EVENT_ANTHROPIC_STREAM_ERROR, error_type="NotConfigured")
        return LlmNotConfiguredError()
    logger.warning(EVENT_ANTHROPIC_STREAM_ERROR, error_type="ContentBlockedError")
    return LlmContentBlockedError()


def _schema_to_json_schema(schema: types.Schema) -> dict[str, object]:
    result: dict[str, object] = {}
    if schema.type is not None:
        result["type"] = schema.type.value.lower()
    if schema.description:
        result["description"] = schema.description
    if schema.enum:
        result["enum"] = list(schema.enum)
    if schema.max_length is not None:
        result["maxLength"] = int(schema.max_length)
    if schema.items is not None:
        result["items"] = _schema_to_json_schema(schema.items)
    if schema.properties:
        result["properties"] = {
            key: _schema_to_json_schema(sub) for key, sub in schema.properties.items()
        }
    if schema.required:
        result["required"] = list(schema.required)
    return result


def _declaration_to_tool(decl: types.FunctionDeclaration) -> dict[str, object]:
    parameters = _schema_to_json_schema(decl.parameters) if decl.parameters else {}
    return {
        "name": decl.name or "",
        "description": decl.description or "",
        "input_schema": parameters or {"type": "object", "properties": {}},
    }


def _build_tools(tools: list[types.Tool] | None) -> list[dict[str, object]]:
    declarations = [
        decl for tool in tools or [] for decl in tool.function_declarations or []
    ]
    anthropic_tools = [_declaration_to_tool(decl) for decl in declarations]
    if anthropic_tools:
        anthropic_tools[-1]["cache_control"] = CACHE_CONTROL
    return anthropic_tools


def _build_messages(contents: list[types.Content]) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for content in contents:
        role = "assistant" if content.role == "model" else "user"
        text = "".join(part.text for part in content.parts or [] if part.text)
        messages.append({"role": role, "content": text})
    return messages


def _build_request(
    system_instruction: str,
    contents: list[types.Content],
    tools: list[types.Tool] | None,
    max_output_tokens: int | None = None,
) -> dict[str, object]:
    # NOTE: temperature, top_p and top_k are never sent — Haiku 5.5 rejects
    # every non-default value with a 400.
    request: dict[str, object] = {
        "model": settings.anthropic_model_name,
        "max_tokens": max_output_tokens or settings.anthropic_max_output_tokens,
        "system": [
            {"type": "text", "text": system_instruction, "cache_control": CACHE_CONTROL}
        ],
        "messages": _build_messages(contents),
        "output_config": {"effort": settings.anthropic_effort},
    }
    anthropic_tools = _build_tools(tools)
    if anthropic_tools:
        request["tools"] = anthropic_tools
        request["tool_choice"] = {"type": "auto"}
    return request


def _text_chunk(text: str) -> types.GenerateContentResponse:
    content = types.Content(role="model", parts=[types.Part(text=text)])
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content)])


def _function_call_chunk(
    tool_id: str, name: str, raw_input: str
) -> types.GenerateContentResponse:
    try:
        args = json.loads(raw_input) if raw_input else {}
    except json.JSONDecodeError:
        logger.warning(EVENT_ANTHROPIC_STREAM_ERROR, error_type="MalformedToolInput")
        args = {}
    part = types.Part(
        function_call=types.FunctionCall(id=tool_id, name=name, args=args)
    )
    content = types.Content(role="model", parts=[part])
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content)])


class _EventTranslator:
    """Turns raw Messages stream events into google.genai chunks."""

    def __init__(self, usage_sink: TokenUsage | None) -> None:
        self._usage_sink = usage_sink
        self._tool_blocks: dict[int, dict[str, str]] = {}
        self._input_tokens = 0
        self._cache_read_tokens = 0
        self._cache_write_tokens = 0
        self._output_tokens = 0

    def translate(
        self, event: RawMessageStreamEvent
    ) -> types.GenerateContentResponse | None:
        match event:
            case RawMessageStartEvent():
                self._on_message_start(event)
            case RawContentBlockStartEvent():
                self._on_block_start(event)
            case RawContentBlockDeltaEvent():
                return self._on_block_delta(event)
            case RawContentBlockStopEvent():
                return self._on_block_stop(event)
            case RawMessageDeltaEvent():
                self._on_message_delta(event)
        return None

    def _on_message_start(self, event: RawMessageStartEvent) -> None:
        usage = event.message.usage
        self._input_tokens = usage.input_tokens or 0
        self._cache_read_tokens = usage.cache_read_input_tokens or 0
        self._cache_write_tokens = usage.cache_creation_input_tokens or 0
        self._output_tokens = usage.output_tokens or 0

    def _on_block_start(self, event: RawContentBlockStartEvent) -> None:
        block = event.content_block
        if isinstance(block, ToolUseBlock):
            self._tool_blocks[event.index] = {
                "id": block.id,
                "name": block.name,
                "input": "",
            }

    def _on_block_delta(
        self, event: RawContentBlockDeltaEvent
    ) -> types.GenerateContentResponse | None:
        delta = event.delta
        if isinstance(delta, TextDelta) and delta.text:
            return _text_chunk(delta.text)
        if isinstance(delta, InputJSONDelta):
            self._tool_blocks[event.index]["input"] += delta.partial_json
        return None

    def _on_block_stop(
        self, event: RawContentBlockStopEvent
    ) -> types.GenerateContentResponse | None:
        block = self._tool_blocks.pop(event.index, None)
        if block is None:
            return None
        return _function_call_chunk(block["id"], block["name"], block["input"])

    def _on_message_delta(self, event: RawMessageDeltaEvent) -> None:
        if event.usage.output_tokens is not None:
            self._output_tokens = event.usage.output_tokens
        if event.delta.stop_reason == STOP_REASON_REFUSAL:
            logger.warning(EVENT_ANTHROPIC_STREAM_ERROR, error_type="Refusal")
            raise LlmContentBlockedError()

    def record_usage(self) -> None:
        prompt_tokens = (
            self._input_tokens + self._cache_read_tokens + self._cache_write_tokens
        )
        logger.info(
            EVENT_ANTHROPIC_STREAM_USAGE,
            model=settings.anthropic_model_name,
            prompt_tokens=prompt_tokens,
            output_tokens=self._output_tokens,
            cache_read_tokens=self._cache_read_tokens,
            cache_write_tokens=self._cache_write_tokens,
        )
        if self._usage_sink is not None:
            self._usage_sink.prompt_tokens = prompt_tokens
            self._usage_sink.completion_tokens = self._output_tokens
            self._usage_sink.model_name = settings.anthropic_model_name


async def _events_within_timeout(
    stream: AsyncIterator[RawMessageStreamEvent], timeout_seconds: int
) -> AsyncIterator[RawMessageStreamEvent]:
    """Yield events as they arrive, bounding each event's wait (never buffers)."""
    events = stream.__aiter__()
    while True:
        try:
            yield await asyncio.wait_for(events.__anext__(), timeout_seconds)
        except StopAsyncIteration:
            return


async def _translated_chunks(
    stream: AsyncIterator[RawMessageStreamEvent],
    translator: _EventTranslator,
    timeout_seconds: int,
) -> AsyncIterator[types.GenerateContentResponse]:
    async for event in _events_within_timeout(stream, timeout_seconds):
        chunk = translator.translate(event)
        if chunk is not None:
            yield chunk


async def _stream_chunks(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None,
    max_output_tokens: int | None = None,
) -> AsyncIterator[types.GenerateContentResponse]:
    request = _build_request(system_instruction, contents, tools, max_output_tokens)
    logger.info(EVENT_ANTHROPIC_STREAM_OPENED, model=settings.anthropic_model_name)
    translator = _EventTranslator(usage_sink)
    with _translated_errors():
        stream = await _get_client().messages.create(
            **request, stream=True, timeout=float(timeout_seconds)
        )
        async for chunk in _translated_chunks(stream, translator, timeout_seconds):
            yield chunk
        translator.record_usage()


async def stream_with_tools(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None = None,
    max_output_tokens: int | None = None,
) -> AsyncIterator[types.GenerateContentResponse]:
    """Stream one master-mode call: text chunks, then complete FunctionCall chunks."""
    async for chunk in _stream_chunks(
        system_instruction,
        contents,
        timeout_seconds,
        tools,
        usage_sink,
        max_output_tokens,
    ):
        yield chunk


async def stream_narration(
    system_instruction: str,
    prompt: str,
    timeout_seconds: int,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Stream narration text for a single player prompt."""
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    async for chunk in _stream_chunks(
        system_instruction, contents, timeout_seconds, None, usage_sink
    ):
        if chunk.text:
            yield chunk.text
