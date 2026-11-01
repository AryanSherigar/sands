"""Tests for app.integrations.anthropic_extraction_client; HTTP is mocked at the transport."""

import json
from collections.abc import Callable

import httpx2
import pytest
import structlog
from anthropic import AsyncAnthropicVertex
from app.config import Settings
from app.exceptions.extraction_exceptions import (
    ExtractionConfigError,
    ExtractionInvalidOutputError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionTransientError,
)
from app.integrations.anthropic_extraction_client import AnthropicExtractionClient
from app.integrations.extraction_client import build_extraction_client
from app.integrations.muse_extraction_client import MuseExtractionClient

TEST_MODEL = "claude-haiku-5-5"
INPUT_CANARY = "CANARY-INPUT-TEXT"
EMPTY_OUTPUT = {
    "new_entities": [],
    "facts": [],
    "supersessions": [],
    "new_commitments": [],
    "commitment_updates": [],
    "scene": None,
}
JUDGE_OUTPUT = {
    "judgements": [
        {"new_fact_index": 0, "superseded_fact_id": None, "reason": "unrelated"}
    ]
}


def _message(
    text: str, stop_reason: str = "end_turn", cache_read: int = 0, cache_write: int = 0
) -> dict[str, object]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": TEST_MODEL,
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_write,
        },
    }


class _Recorder:
    def __init__(self) -> None:
        self.bodies: list[dict[str, object]] = []


def _client_with(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> tuple[AnthropicExtractionClient, _Recorder]:
    recorder = _Recorder()

    def recording_handler(request: httpx2.Request) -> httpx2.Response:
        recorder.bodies.append(json.loads(request.content))
        return handler(request)

    client = AnthropicExtractionClient(
        model_name=TEST_MODEL,
        timeout_seconds=5,
        max_tokens=1024,
        effort="low",
        project="test-project",
    )
    client._sdk_client = AsyncAnthropicVertex(
        region="global",
        project_id="test-project",
        access_token="test-token",
        http_client=httpx2.AsyncClient(
            transport=httpx2.MockTransport(recording_handler)
        ),
        max_retries=0,
    )
    return client, recorder


def _ok(payload: dict[str, object], **usage: int) -> Callable[..., httpx2.Response]:
    return lambda request: httpx2.Response(
        200, json=_message(json.dumps(payload), **usage)
    )


def _status(code: int) -> Callable[..., httpx2.Response]:
    body = {"type": "error", "error": {"type": "api_error", "message": INPUT_CANARY}}
    return lambda request: httpx2.Response(code, json=body)


async def test_extract_returns_validated_output_and_usage() -> None:
    client, _ = _client_with(_ok(EMPTY_OUTPUT, cache_read=300, cache_write=50))

    result = await client.extract("system", "user")

    assert result.output.facts == []
    assert result.raw_output == EMPTY_OUTPUT
    assert result.usage.input_tokens == 361
    assert result.usage.output_tokens == 7
    assert result.usage.cached_tokens == 300


async def test_request_uses_schema_output_cache_control_and_no_sampling() -> None:
    client, recorder = _client_with(_ok(EMPTY_OUTPUT))

    await client.extract("system prompt", "user content")

    body = recorder.bodies[0]
    for forbidden in ("temperature", "top_p", "top_k"):
        assert forbidden not in body
    assert body["max_tokens"] == 1024
    assert body["system"] == [
        {
            "type": "text",
            "text": "system prompt",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    assert body["messages"] == [{"role": "user", "content": "user content"}]
    assert body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "facts" in body["output_config"]["format"]["schema"]["properties"]


async def test_judge_supersessions_returns_validated_output() -> None:
    client, recorder = _client_with(_ok(JUDGE_OUTPUT))

    result = await client.judge_supersessions("system", "user")

    assert result.output.judgements[0].reason == "unrelated"
    schema = recorder.bodies[0]["output_config"]["format"]["schema"]
    assert "judgements" in schema["properties"]


async def test_invalid_json_raises_invalid_output() -> None:
    client, _ = _client_with(
        lambda request: httpx2.Response(200, json=_message("not json"))
    )

    with pytest.raises(ExtractionInvalidOutputError):
        await client.extract("system", "user")


async def test_schema_violation_raises_invalid_output() -> None:
    client, _ = _client_with(_ok({"facts": "nope"}))

    with pytest.raises(ExtractionInvalidOutputError):
        await client.extract("system", "user")


async def test_refusal_raises_permanent() -> None:
    client, _ = _client_with(
        lambda request: httpx2.Response(200, json=_message("", stop_reason="refusal"))
    )

    with pytest.raises(ExtractionPermanentError):
        await client.extract("system", "user")


async def test_truncated_output_raises_invalid_output() -> None:
    client, _ = _client_with(
        lambda request: httpx2.Response(
            200, json=_message('{"facts": [', stop_reason="max_tokens")
        )
    )

    with pytest.raises(ExtractionInvalidOutputError):
        await client.extract("system", "user")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (429, ExtractionRateLimitedError),
        (500, ExtractionTransientError),
        (529, ExtractionTransientError),
        (400, ExtractionConfigError),
        (401, ExtractionConfigError),
        (403, ExtractionConfigError),
        (404, ExtractionConfigError),
        (422, ExtractionPermanentError),
    ],
)
async def test_http_errors_map_to_extraction_errors(
    status: int, expected: type[Exception]
) -> None:
    client, recorder = _client_with(_status(status))

    with pytest.raises(expected):
        await client.extract("system", "user")

    assert len(recorder.bodies) == 1


async def test_logs_and_errors_never_contain_prompt_or_provider_text() -> None:
    client, _ = _client_with(_status(400))

    with (
        structlog.testing.capture_logs() as logs,
        pytest.raises(ExtractionConfigError) as raised,
    ):
        await client.extract("system", INPUT_CANARY)

    assert INPUT_CANARY not in str(raised.value)
    assert INPUT_CANARY not in json.dumps(logs, default=str)


def test_factory_defaults_to_muse_provider() -> None:
    settings = Settings(_env_file=None, extraction_api_key="test-key")

    assert isinstance(build_extraction_client(settings), MuseExtractionClient)


def test_factory_builds_anthropic_client_from_provider_flag() -> None:
    settings = Settings(
        _env_file=None,
        extraction_provider="anthropic",
        vertex_project="my-project",
        anthropic_extraction_max_tokens=2048,
    )

    client = build_extraction_client(settings)

    assert isinstance(client, AnthropicExtractionClient)
    assert client.model_name == "claude-haiku-5-5"
