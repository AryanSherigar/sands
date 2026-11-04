"""Unit tests for text_gen_client.py with the Muse chat endpoint mocked."""

import json

import httpx
import pytest
import respx
from app.exceptions.text_generation_exceptions import TextGenerationError
from app.integrations import text_gen_client

_MUSE_URL = "https://api.meta.ai/v1/chat/completions"


@pytest.fixture(autouse=True)
def muse_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text_gen_client.settings, "muse_api_key", "test-key")
    monkeypatch.setattr(
        text_gen_client.settings, "muse_base_url", "https://api.meta.ai/v1"
    )


def _completion(content: str | None, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {"role": "assistant", "content": content},
                }
            ]
        },
    )


@respx.mock
async def test_generate_text_returns_stripped_content_and_sends_request() -> None:
    route = respx.post(_MUSE_URL).mock(
        return_value=_completion("  A crown of ash.  \n")
    )

    result = await text_gen_client.generate_text("Write a chronicle", 180, 5)

    assert result == "A crown of ash."
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == text_gen_client.settings.muse_text_model_name
    assert body["messages"] == [{"role": "user", "content": "Write a chronicle"}]
    assert (
        body["reasoning_effort"] == text_gen_client.settings.muse_text_reasoning_effort
    )
    assert body["max_completion_tokens"] == 180 + (
        text_gen_client.REASONING_HEADROOM_TOKENS
    )


@respx.mock
@pytest.mark.parametrize("status_code", [400, 401, 429, 500, 503])
async def test_error_status_raises_text_generation_error(status_code: int) -> None:
    respx.post(_MUSE_URL).mock(return_value=httpx.Response(status_code))

    with pytest.raises(TextGenerationError):
        await text_gen_client.generate_text("prompt", 100, 5)


@respx.mock
async def test_timeout_raises_text_generation_error() -> None:
    respx.post(_MUSE_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(TextGenerationError):
        await text_gen_client.generate_text("prompt", 100, 5)


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        _completion(None),
        _completion(""),
        _completion("cut off", finish_reason="length"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={}),
    ],
)
async def test_unusable_completion_raises_text_generation_error(
    response: httpx.Response,
) -> None:
    respx.post(_MUSE_URL).mock(return_value=response)

    with pytest.raises(TextGenerationError):
        await text_gen_client.generate_text("prompt", 100, 5)
