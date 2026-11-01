"""Narration provider router for Turn Resolution Service.

Dispatches the three narration call patterns (stream_narration, stream_chat,
stream_with_tools) to openai_compatible_client (Meta Muse) or anthropic_client
based on the NARRATION_PROVIDER setting.

This is the only file ai_orchestrator.py imports for narration. stream_chat has
no Anthropic branch: Studio chat always uses the OpenAI-compatible client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import ModuleType

from app.config import settings
from app.integrations import anthropic_client, openai_compatible_client
from app.models.token_usage import TokenUsage
from google.genai import types


def _narration_module() -> ModuleType:
    if settings.narration_provider == "anthropic":
        return anthropic_client
    return openai_compatible_client


async def stream_narration(
    system_instruction: str,
    prompt: str,
    timeout_seconds: int,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Route streaming narration to the configured provider."""
    async for chunk in _narration_module().stream_narration(
        system_instruction, prompt, timeout_seconds, usage_sink=usage_sink
    ):
        yield chunk


async def stream_chat(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    max_output_tokens: int = 1500,
    usage_sink: TokenUsage | None = None,
) -> AsyncIterator[str]:
    """Route streaming studio-chat to the configured provider."""
    async for chunk in openai_compatible_client.stream_chat(
        system_instruction,
        contents,
        timeout_seconds,
        max_output_tokens,
        usage_sink=usage_sink,
    ):
        yield chunk


async def chat_completion(
    system_prompt: str,
    user_message: str,
    response_format: dict[str, object] | None = None,
    timeout_seconds: int | None = None,
) -> str:
    """Route non-streaming chat completion to the configured provider."""
    return await openai_compatible_client.chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        response_format=response_format,
        timeout_seconds=timeout_seconds,
    )


_RECORD_STATE_DIRECTIVE = (
    "Record the lasting state changes established by the narration above by "
    "calling the tools. Write no prose. If nothing durable changed, call no tool."
)


def _chunk_of(parts: list[types.Part]) -> types.GenerateContentResponse:
    content = types.Content(role="model", parts=parts)
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content)])


def _call_parts(response: types.GenerateContentResponse) -> list[types.Part]:
    return [
        part
        for candidate in response.candidates or []
        for part in candidate.content.parts or []
        if part.function_call
    ]


def _record_contents(
    contents: list[types.Content], narration: str
) -> list[types.Content]:
    return [
        *contents,
        types.Content(role="model", parts=[types.Part(text=narration)]),
        types.Content(role="user", parts=[types.Part(text=_RECORD_STATE_DIRECTIVE)]),
    ]


def _sum_usage(sink: TokenUsage | None, *calls: TokenUsage) -> None:
    if sink is None:
        return
    sink.prompt_tokens = sum(call.prompt_tokens for call in calls)
    sink.completion_tokens = sum(call.completion_tokens for call in calls)
    sink.model_name = next((call.model_name for call in calls if call.model_name), "")


async def _narrate_then_record_stream(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None,
    max_output_tokens: int | None,
) -> AsyncIterator[types.GenerateContentResponse]:
    """Muse writes a one-line stub instead of narration whenever it calls a tool
    in the same response, so narration streams first with no tools and a second
    call records the state changes from the finished prose."""
    narration_usage, record_usage = TokenUsage(), TokenUsage()
    limit_kwargs = (
        {} if max_output_tokens is None else {"max_output_tokens": max_output_tokens}
    )
    narration = ""
    async for text in openai_compatible_client.stream_chat(
        system_instruction,
        contents,
        timeout_seconds,
        usage_sink=narration_usage,
        **limit_kwargs,
    ):
        narration += text
        yield _chunk_of([types.Part(text=text)])
    if tools and narration.strip():
        response = await openai_compatible_client.generate_with_tools(
            system_instruction,
            _record_contents(contents, narration),
            timeout_seconds,
            tools,
            usage_sink=record_usage,
        )
        call_parts = _call_parts(response)
        if call_parts:
            yield _chunk_of(call_parts)
    _sum_usage(usage_sink, narration_usage, record_usage)


async def stream_with_tools(
    system_instruction: str,
    contents: list[types.Content],
    timeout_seconds: int,
    tools: list[types.Tool] | None,
    usage_sink: TokenUsage | None = None,
    max_output_tokens: int | None = None,
) -> AsyncIterator[types.GenerateContentResponse]:
    """Route master-mode tool-calling to the configured provider.

    `max_output_tokens` is a per-scenario override of the provider's default.

    Anthropic streams token-by-token and delivers each function call complete in
    its own chunk. The OpenAI-compatible path streams the narration and then makes
    one non-streaming call for the function calls.
    """
    if settings.narration_provider == "openai":
        stream = _narrate_then_record_stream(
            system_instruction,
            contents,
            timeout_seconds,
            tools,
            usage_sink,
            max_output_tokens,
        )
    else:
        limit_kwargs = (
            {}
            if max_output_tokens is None
            else {"max_output_tokens": max_output_tokens}
        )
        stream = _narration_module().stream_with_tools(
            system_instruction,
            contents,
            timeout_seconds,
            tools,
            usage_sink=usage_sink,
            **limit_kwargs,
        )
    async for chunk in stream:
        yield chunk
