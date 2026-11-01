"""Tests for app.integrations.muse_extraction_client; HTTP is mocked at the transport."""

import json

import httpx
import pytest
from app.config import Settings
from app.exceptions.extraction_exceptions import (
    ExtractionConfigError,
    ExtractionInvalidOutputError,
    ExtractionNotConfiguredError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionTransientError,
)
from app.integrations.extraction_client import build_extraction_client
from app.integrations.muse_extraction_client import MuseExtractionClient

TEST_MODEL = "muse-spark-1.3"
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


def _completion(
    content: str | None, finish_reason: str = "stop", cached_tokens: int = 0
) -> dict[str, object]:
    return {
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
            "prompt_tokens_details": {"cached_tokens": cached_tokens},
        },
    }


def _client(handler, api_key: str = "test-key") -> MuseExtractionClient:
    return MuseExtractionClient(
        api_key=api_key,
        base_url="https://api.meta.ai/v1",
        model_name=TEST_MODEL,
        timeout_seconds=5,
        max_tokens=4096,
        reasoning_effort="minimal",
        transport=httpx.MockTransport(handler),
    )


def _ok(body: dict[str, object]):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    return handler


async def test_extract_parses_output_and_maps_usage() -> None:
    client = _client(_ok(_completion(json.dumps(EMPTY_OUTPUT), cached_tokens=4)))

    result = await client.extract("system", "user")

    assert result.output.facts == []
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 7
    assert result.usage.cached_tokens == 4
    assert client.model_name == TEST_MODEL


async def test_extract_sends_schema_effort_and_messages() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion(json.dumps(EMPTY_OUTPUT)))

    await _client(handler).extract("SYS", "USER")

    body = seen["body"]
    assert seen["auth"] == "Bearer test-key"
    assert seen["url"] == "https://api.meta.ai/v1/chat/completions"
    assert body["model"] == TEST_MODEL
    assert body["reasoning_effort"] == "minimal"
    assert body["max_completion_tokens"] == 4096
    assert body["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    assert body["response_format"]["type"] == "json_schema"
    assert "properties" in body["response_format"]["json_schema"]["schema"]


async def test_judge_supersessions_parses_output() -> None:
    client = _client(_ok(_completion(json.dumps(JUDGE_OUTPUT))))

    result = await client.judge_supersessions("system", "user")

    assert result.output.judgements[0].reason == "unrelated"


@pytest.mark.parametrize("content", [None, "", "not json", '{"facts": "oops"}'])
async def test_unusable_content_raises_invalid_output(content: str | None) -> None:
    client = _client(_ok(_completion(content)))

    with pytest.raises(ExtractionInvalidOutputError):
        await client.extract("system", "user")


async def test_truncated_output_raises_invalid_output() -> None:
    client = _client(_ok(_completion('{"facts": [', finish_reason="length")))

    with pytest.raises(ExtractionInvalidOutputError):
        await client.extract("system", "user")


async def test_content_filter_raises_permanent() -> None:
    client = _client(_ok(_completion(None, finish_reason="content_filter")))

    with pytest.raises(ExtractionPermanentError):
        await client.extract("system", "user")


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (429, ExtractionRateLimitedError),
        (500, ExtractionTransientError),
        (503, ExtractionTransientError),
        (504, ExtractionTransientError),
        (400, ExtractionConfigError),
        (401, ExtractionConfigError),
        (404, ExtractionConfigError),
        (422, ExtractionPermanentError),
    ],
)
async def test_http_errors_are_classified(
    status_code: int, expected: type[Exception]
) -> None:
    client = _client(lambda request: httpx.Response(status_code, json={"error": {}}))

    with pytest.raises(expected):
        await client.extract("system", "user")


async def test_timeout_raises_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ExtractionTransientError):
        await _client(handler).extract("system", "user")


def test_blank_api_key_is_not_configured() -> None:
    with pytest.raises(ExtractionNotConfiguredError):
        _client(_ok({}), api_key="  ")


def test_factory_builds_muse_client_for_muse_provider() -> None:
    settings = Settings(
        _env_file=None, extraction_provider="muse", muse_api_key="test-key"
    )

    client = build_extraction_client(settings)

    assert isinstance(client, MuseExtractionClient)
    assert client.model_name == settings.extraction_model_name


def test_factory_returns_none_for_muse_without_key() -> None:
    settings = Settings(
        _env_file=None, extraction_provider="muse", extraction_api_key=None
    )

    assert build_extraction_client(settings) is None
