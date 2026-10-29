"""Gemini narration client for Turn Resolution Service.

Real Vertex AI wiring, via the google-genai SDK, authenticated with a Vertex
AI API key (Express Mode) rather than Application Default Credentials. The
only file `ai_orchestrator.py` is permitted to call (CLAUDE.md). The key
(`GEMINI_API_KEY`) is read only from `app.config`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog
from app.config import settings
from app.exceptions.turn_exceptions import (
    LlmContentBlockedError,
    LlmUnavailableError,
)
from app.models.token_usage import TokenUsage
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = structlog.get_logger()

# NOTE: only ever log Gemini call metadata here (model, error type) — never
# the prompt or generated narration text, per the redaction policy in
# docs/logging.md. This is the one place in the codebase handling raw model
# output, so the discipline has to hold here specifically.
EVENT_GEMINI_STREAM_OPENED = "gemini_stream_opened"
EVENT_GEMINI_STREAM_ERROR = "gemini_stream_error"
EVENT_GEMINI_STREAM_USAGE = "gemini_stream_usage"

_HARM_CATEGORIES: list[types.HarmCategory] = [
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    types.HarmCategory.HARM_CATEGORY_HARASSMENT,
]

_SAFETY_SETTINGS: list[types.SafetySetting] = [
    types.SafetySetting(
        category=category, threshold=types.HarmBlockThreshold.BLOCK_NONE
    )
    for category in _HARM_CATEGORIES
]

_client: genai.Client | None = None

_RATE_LIMIT_STATUS_CODE = 429
_CONTENT_BLOCKED_STATUS_CODES = (400, 403)


def _build_client() -> genai.Client:
    if settings.is_vertex_adc_enabled:
        return genai.Client(
            vertexai=True,
            project=settings.google_cloud_project or None,
            location=settings.google_cloud_location,
        )
    return genai.Client(vertexai=True, api_key=settings.gemini_api_key)


def _get_client() -> genai.Client:
    """Build the Vertex AI client lazily and cache it.

    Uses the service account (ADC) when `is_vertex_adc_enabled`, else the
    API key (Express Mode). Constructing genai.Client(...) validates its
    credentials eagerly — doing that at import time would make importing this
    module fail in any environment without them (tests, CI).
    """
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _record_chunk_usage(
    chunk: types.GenerateContentResponse, usage_sink: TokenUsage | None
) -> None:
    if usage_sink is None or not hasattr(chunk, "usage_metadata"):
        return
    meta = chunk.usage_metadata
    if meta is None:
        return
    if getattr(meta, "prompt_token_count", None) is not None:
        usage_sink.prompt_tokens = meta.prompt_token_count
    if getattr(meta, "candidates_token_count", None) is not None:
        usage_sink.completion_tokens = meta.candidates_token_count
    usage_sink.model_name = settings.gemini_model_name


async def stream_with_tools(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None = None,
    max_output_tokens: int | None = None,
) -> AsyncIterator[types.GenerateContentResponse]:
    """Stream a single master-mode function-calling call, tools included.

    A function-call part arrives as one complete, unfragmented chunk (never
    split token-by-token the way text does) in its own chunk with no text
    alongside it — verified directly against the SDK before this was built.
    Callers inspect `.function_calls` on each yielded chunk; text chunks
    carry narration, the one function-call-bearing chunk (if any) carries the
    model's tool calls.

    Manual function calling only (automatic_function_calling.disable=True):
    the caller — not the SDK — decides whether each proposed mutation is
    valid, in a single pass over this one call's result (ADR-4).
    """
    config = _build_generation_config(system_instruction, max_output_tokens)
    if tools:
        config.tools = tools
        config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
            disable=True
        )
    logger.info(EVENT_GEMINI_STREAM_OPENED, model=settings.gemini_model_name)
    try:
        async for chunk in _stream_within_timeout(contents, config, timeout_seconds):
            _record_chunk_usage(chunk, usage_sink)
            yield chunk
    except asyncio.TimeoutError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="TimeoutError")
        raise LlmUnavailableError() from exc
    except genai_errors.ServerError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="ServerError")
        raise LlmUnavailableError() from exc
    except genai_errors.ClientError as exc:
        if exc.code == _RATE_LIMIT_STATUS_CODE:
            logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="RateLimitError")
            raise LlmUnavailableError() from exc
        if exc.code in _CONTENT_BLOCKED_STATUS_CODES:
            logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="ContentBlockedError")
            raise LlmContentBlockedError() from exc
        raise


async def stream_narration(
    system_instruction: str,
    prompt: str,
    timeout_seconds: int,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Stream narration chunks for the given prompt from Gemini on Vertex AI."""
    config = _build_generation_config(system_instruction)
    logger.info(EVENT_GEMINI_STREAM_OPENED, model=settings.gemini_model_name)
    try:
        async for chunk in _stream_within_timeout(prompt, config, timeout_seconds):
            _record_chunk_usage(chunk, usage_sink)
            if chunk.text:
                yield chunk.text
    except asyncio.TimeoutError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="TimeoutError")
        raise LlmUnavailableError() from exc
    except genai_errors.ServerError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="ServerError")
        raise LlmUnavailableError() from exc
    except genai_errors.ClientError as exc:
        if exc.code == _RATE_LIMIT_STATUS_CODE:
            logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="RateLimitError")
            raise LlmUnavailableError() from exc
        if exc.code in _CONTENT_BLOCKED_STATUS_CODES:
            logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="ContentBlockedError")
            raise LlmContentBlockedError() from exc
        raise


async def stream_chat(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    max_output_tokens: int = 1500,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Stream chat response chunks for multi-turn studio assistant."""
    config = _build_generation_config(
        system_instruction, max_output_tokens=max_output_tokens
    )
    logger.info(EVENT_GEMINI_STREAM_OPENED, model=settings.gemini_model_name)
    try:
        async for chunk in _stream_within_timeout(contents, config, timeout_seconds):
            _record_chunk_usage(chunk, usage_sink)
            if chunk.text:
                yield chunk.text
    except asyncio.TimeoutError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="TimeoutError")
        raise LlmUnavailableError() from exc
    except genai_errors.ServerError as exc:
        logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="ServerError")
        raise LlmUnavailableError() from exc
    except genai_errors.ClientError as exc:
        if exc.code == _RATE_LIMIT_STATUS_CODE:
            logger.warning(EVENT_GEMINI_STREAM_ERROR, error_type="RateLimitError")
            raise LlmUnavailableError() from exc
        raise


async def _stream_within_timeout(
    contents: str | list[types.Content],
    config: types.GenerateContentConfig,
    timeout_seconds: int,
) -> AsyncIterator[types.GenerateContentResponse]:
    """Yield chunks as they arrive, bounding each chunk's wait (never buffers the stream)."""
    stream = await _get_client().aio.models.generate_content_stream(
        model=settings.gemini_model_name, contents=contents, config=config
    )
    stream_iterator = stream.__aiter__()
    usage: types.GenerateContentResponseUsageMetadata | None = None
    while True:
        try:
            chunk = await asyncio.wait_for(
                stream_iterator.__anext__(), timeout=timeout_seconds
            )
        except StopAsyncIteration:
            _log_stream_usage(usage)
            return
        usage = getattr(chunk, "usage_metadata", None) or usage
        yield chunk


def _log_stream_usage(usage: types.GenerateContentResponseUsageMetadata | None) -> None:
    if usage is None:
        return
    logger.info(
        EVENT_GEMINI_STREAM_USAGE,
        model=settings.gemini_model_name,
        prompt_tokens=usage.prompt_token_count,
        output_tokens=usage.candidates_token_count,
        thoughts_tokens=usage.thoughts_token_count,
        cached_tokens=usage.cached_content_token_count,
    )


def _build_generation_config(
    system_instruction: str, max_output_tokens: int | None = None
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=settings.gemini_temperature,
        max_output_tokens=max_output_tokens or settings.gemini_max_output_tokens,
        top_p=settings.gemini_top_p,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel(settings.gemini_thinking_level.upper())
        ),
        safety_settings=_SAFETY_SETTINGS,
    )
