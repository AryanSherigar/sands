"""Unit tests for the Muse image_gen_client.py, with the Muse endpoint mocked."""

import base64
import json

import httpx
import pytest
import respx
from app.exceptions.turn_exceptions import SceneImageGenerationError
from app.integrations import image_gen_client

_MUSE_URL = "https://api.meta.ai/v1/images/generations"


@pytest.fixture(autouse=True)
def muse_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_gen_client.settings, "muse_api_key", "test-key")
    monkeypatch.setattr(
        image_gen_client.settings, "muse_base_url", "https://api.meta.ai/v1"
    )


@respx.mock
async def test_generate_image_returns_decoded_bytes_and_sends_request() -> None:
    encoded = base64.b64encode(b"muse-webp-bytes").decode()
    route = respx.post(_MUSE_URL).mock(
        return_value=httpx.Response(200, json={"data": [{"b64_json": encoded}]})
    )

    result = await image_gen_client.generate_image("a quiet harbor", 5)

    assert result == b"muse-webp-bytes"
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "muse-image-1.0"
    assert body["prompt"] == "a quiet harbor"
    assert body["output_format"] == "webp"
    assert body["reasoning_strength"] == "low"
    assert body["n"] == 1


@respx.mock
@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
async def test_error_status_raises_scene_image_error(status_code: int) -> None:
    respx.post(_MUSE_URL).mock(
        return_value=httpx.Response(status_code, json={"error": {"message": "no"}})
    )

    with pytest.raises(SceneImageGenerationError):
        await image_gen_client.generate_image("a scene", 5)


@respx.mock
async def test_timeout_raises_scene_image_error() -> None:
    respx.post(_MUSE_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(SceneImageGenerationError):
        await image_gen_client.generate_image("a scene", 5)


@respx.mock
@pytest.mark.parametrize(
    "body",
    [{"data": []}, {}, {"data": [{"b64_json": ""}]}, {"data": [{"b64_json": "!!"}]}],
)
async def test_unusable_body_raises_scene_image_error(body: dict[str, object]) -> None:
    respx.post(_MUSE_URL).mock(return_value=httpx.Response(200, json=body))

    with pytest.raises(SceneImageGenerationError):
        await image_gen_client.generate_image("a scene", 5)


def test_output_type_is_webp() -> None:
    assert image_gen_client.output_content_type() == "image/webp"
    assert image_gen_client.output_extension() == ".webp"
