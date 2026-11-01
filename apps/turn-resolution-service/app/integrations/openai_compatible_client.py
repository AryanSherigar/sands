"""OpenAI-compatible narration client for Turn Resolution Service.

Implements the same public interface as gemini_client.py so that
narration_router.py can dispatch to it transparently. Calls any provider
exposing an OpenAI Chat Completions endpoint via the openai>=3.0.0 SDK.

Configuration is read exclusively from app.config (CLAUDE.md):
  OPENAI_COMPATIBLE_BASE_URL, OPENAI_COMPATIBLE_API_KEY,
  OPENAI_COMPATIBLE_MODEL_NAME.

Error mapping keeps the caller interface identical to the Gemini path:
  openai.APITimeoutError | openai.APIConnectionError → LlmUnavailableError
  openai.RateLimitError                              → LlmUnavailableError
  openai.BadRequestError | openai.PermissionDeniedError → LlmContentBlockedError
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

import openai
import structlog
from app.config import settings
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmUnavailableError,
)
from app.models.token_usage import TokenUsage
from google.genai import types

logger = structlog.get_logger()

EVENT_OPENAI_STREAM_OPENED = "openai_stream_opened"
EVENT_OPENAI_STREAM_ERROR = "openai_stream_error"

_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    """Build the AsyncOpenAI client lazily and cache it.

    Constructed at first call so that importing this module in environments
    without the OpenAI env vars set (tests, Gemini-only deployments) does not
    raise immediately.
    """
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(
            base_url=settings.openai_compatible_base_url,
            api_key=settings.openai_compatible_api_key,
            timeout=float(settings.narration_timeout_seconds),
            max_retries=0,
        )
    return _client


@contextmanager
def _mapped_errors() -> Iterator[None]:
    """Translate SDK errors into the domain errors every caller already handles."""
    try:
        yield
    except (openai.APITimeoutError, openai.APIConnectionError) as exc:
        logger.warning(EVENT_OPENAI_STREAM_ERROR, error_type="Unavailable")
        raise LlmUnavailableError() from exc
    except openai.RateLimitError as exc:
        logger.warning(EVENT_OPENAI_STREAM_ERROR, error_type="RateLimit")
        raise LlmUnavailableError() from exc
    except (openai.BadRequestError, openai.PermissionDeniedError) as exc:
        logger.warning(EVENT_OPENAI_STREAM_ERROR, error_type="ContentBlocked")
        raise LlmContentBlockedError() from exc
    except openai.APIStatusError as exc:
        logger.warning(
            EVENT_OPENAI_STREAM_ERROR, error_type="Status", status=exc.status_code
        )
        raise LlmUnavailableError() from exc


def _reasoning_kwargs() -> dict[str, object]:
    effort = settings.openai_compatible_reasoning_effort
    return {"reasoning_effort": effort} if effort else {}


def _cached_tokens(usage: object) -> int:
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0)
    return cached if isinstance(cached, int) else 0


def _record_openai_usage(
    usage_container: object, usage_sink: TokenUsage | None
) -> None:
    if usage_sink is not None and getattr(usage_container, "usage", None):
        usage = usage_container.usage
        usage_sink.prompt_tokens = usage.prompt_tokens
        usage_sink.completion_tokens = usage.completion_tokens
        usage_sink.cached_tokens = _cached_tokens(usage)
        usage_sink.model_name = settings.openai_compatible_model_name


async def stream_narration(
    system_instruction: str,
    prompt: str,
    timeout_seconds: int,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Stream narration chunks from an OpenAI-compatible endpoint."""
    logger.info(EVENT_OPENAI_STREAM_OPENED, model=settings.openai_compatible_model_name)
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt},
    ]
    with _mapped_errors():
        async for chunk in _stream_chat_completions(
            messages, timeout_seconds, usage_sink=usage_sink
        ):
            yield chunk


async def stream_chat(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    max_output_tokens: int = 1500,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Stream studio-chat response chunks from an OpenAI-compatible endpoint."""
    logger.info(EVENT_OPENAI_STREAM_OPENED, model=settings.openai_compatible_model_name)
    messages = _gemini_contents_to_openai_messages(system_instruction, contents)
    with _mapped_errors():
        async for chunk in _stream_chat_completions(
            messages,
            timeout_seconds,
            max_tokens=max_output_tokens,
            usage_sink=usage_sink,
        ):
            yield chunk


async def chat_completion(
    system_prompt: str,
    user_message: str,
    response_format: dict[str, object] | None = None,
    timeout_seconds: int | None = None,
) -> str:
    """Non-streaming chat completion returning raw content text."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    timeout = float(timeout_seconds or settings.narration_timeout_seconds)
    kwargs: dict[str, object] = {
        "model": settings.openai_compatible_model_name,
        "messages": messages,
        "timeout": timeout,
        **_reasoning_kwargs(),
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    with _mapped_errors():
        client = _get_client()
        response = await client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
    choice = response.choices[0]
    return choice.message.content or ""


async def generate_with_tools(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None = None,
) -> types.GenerateContentResponse:
    """Single non-streaming tool-calling round-trip for master-mode.

    Translates Gemini types in → OpenAI request → Gemini types out so
    ai_orchestrator.py's master-mode loop is unchanged.
    """
    logger.info(EVENT_OPENAI_STREAM_OPENED, model=settings.openai_compatible_model_name)
    messages = _gemini_contents_to_openai_messages(system_instruction, contents)
    openai_tools = _gemini_tools_to_openai(tools) if tools else None
    with _mapped_errors():
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.openai_compatible_model_name,
            messages=messages,  # type: ignore[arg-type]
            tools=openai_tools,  # type: ignore[arg-type]
            tool_choice="auto" if openai_tools else openai.NOT_GIVEN,
            timeout=float(timeout_seconds),
            **_reasoning_kwargs(),
        )
    _record_openai_usage(response, usage_sink)
    return _openai_response_to_gemini(response)


async def _stream_chat_completions(
    messages: list[dict[str, str]],
    timeout_seconds: int,
    max_tokens: int | None = None,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Yield text delta strings from a streaming Chat Completions response."""
    kwargs: dict[str, object] = {
        "model": settings.openai_compatible_model_name,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "timeout": float(timeout_seconds),
        **_reasoning_kwargs(),
    }
    if max_tokens is not None:
        kwargs["max_completion_tokens"] = max_tokens
    client = _get_client()
    stream = await client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
    async for chunk in stream:
        _record_openai_usage(chunk, usage_sink)
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _gemini_contents_to_openai_messages(
    system_instruction: str,
    contents: list[types.Content],
) -> list[dict[str, str]]:
    """Convert Gemini Content list + system instruction to OpenAI messages list."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system_instruction}]
    for content in contents:
        role = "assistant" if content.role == "model" else "user"
        text_parts = [
            part.text
            for part in (content.parts or [])
            if isinstance(part, types.Part) and part.text
        ]
        messages.append({"role": role, "content": " ".join(text_parts)})
    return messages


def _gemini_tools_to_openai(tools: list[types.Tool]) -> list[dict[str, object]]:
    """Convert Gemini types.Tool list to OpenAI tools array (JSON Schema format)."""
    openai_tools: list[dict[str, object]] = []
    for tool in tools:
        for decl in tool.function_declarations or []:
            openai_tools.append(_function_declaration_to_openai(decl))
    return openai_tools


def _function_declaration_to_openai(
    decl: types.FunctionDeclaration,
) -> dict[str, object]:
    """Convert a single FunctionDeclaration to an OpenAI function tool dict."""
    parameters = _schema_to_json_schema(decl.parameters) if decl.parameters else {}
    return {
        "type": "function",
        "function": {
            "name": decl.name or "",
            "description": decl.description or "",
            "parameters": parameters,
        },
    }


def _schema_to_json_schema(schema: types.Schema) -> dict[str, object]:
    """Recursively convert a Gemini types.Schema to a plain JSON Schema dict."""
    result: dict[str, object] = {}
    if schema.type is not None:
        result["type"] = schema.type.value.lower()
    if schema.description:
        result["description"] = schema.description
    if schema.properties:
        result["properties"] = {
            key: _schema_to_json_schema(sub) for key, sub in schema.properties.items()
        }
    if schema.required:
        result["required"] = list(schema.required)
    return result


def _openai_response_to_gemini(
    response: openai.types.chat.ChatCompletion,
) -> types.GenerateContentResponse:
    """Wrap an OpenAI ChatCompletion in a GenerateContentResponse shape.

    The master-mode loop in ai_orchestrator.py reads .text (final narration)
    and .function_calls (tool requests). This translation covers both cases.
    """
    choice = response.choices[0] if response.choices else None
    if choice is None:
        return types.GenerateContentResponse()

    message = choice.message
    tool_calls = message.tool_calls or []
    text = message.content or ""
    parts = [_openai_tool_call_to_part(call) for call in tool_calls]
    if text or not parts:
        parts.insert(0, types.Part(text=text))
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts))]
    )


def _openai_tool_call_to_part(
    tool_call: openai.types.chat.chat_completion_message_tool_call.ChatCompletionMessageToolCall,
) -> types.Part:
    """Convert a single OpenAI tool call to a Gemini Part with a FunctionCall."""
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    return types.Part(
        function_call=types.FunctionCall(
            name=tool_call.function.name,
            args=args,
            id=tool_call.id,
        )
    )
