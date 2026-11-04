import base64
import io
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from PIL import Image


@pytest.mark.asyncio
async def test_optimize_prompt_endpoint(async_client: AsyncClient):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    payload = {"description": "Stern Viking chieftain with braided beard"}
    resp = await async_client.post(
        "/v1/studio/avatars/optimize-prompt",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "optimized_prompt" in data
    assert "Viking chieftain" in data["optimized_prompt"]


@pytest.mark.asyncio
async def test_optimize_prompt_endpoint_empty_description(async_client: AsyncClient):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    payload = {"description": ""}
    resp = await async_client.post(
        "/v1/studio/avatars/optimize-prompt",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "optimized_prompt" in data
    assert "portrait" in data["optimized_prompt"].lower()


@pytest.mark.asyncio
async def test_optimize_prompt_endpoint_unauthenticated(async_client: AsyncClient):
    payload = {"description": "Stern Viking chieftain with braided beard"}
    resp = await async_client.post(
        "/v1/studio/avatars/optimize-prompt",
        json=payload,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_build_mesh_endpoint_success(async_client: AsyncClient, monkeypatch):
    image = io.BytesIO()
    Image.new("RGB", (16, 16)).save(image, format="PNG")
    encoded = base64.b64encode(image.getvalue()).decode()
    monkeypatch.setattr(
        "app.routers.studio_avatar_router.storage_client.upload_public_bytes",
        AsyncMock(return_value="https://example.com/avatar.mavatar"),
    )
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    payload = {
        "name": "Queen Mira",
        "image_url": f"data:image/png;base64,{encoded}",
    }
    resp = await async_client.post(
        "/v1/studio/avatars/build-mesh",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Queen Mira"
    assert "avatar_url" in data
    assert data["avatar_url"].endswith(".mavatar")


@pytest.mark.asyncio
async def test_build_mesh_rejects_remote_input(async_client: AsyncClient):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    resp = await async_client.post(
        "/v1/studio/avatars/build-mesh",
        json={"name": "Mira", "image_url": "http://127.0.0.1/private"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_build_mesh_endpoint_unauthenticated(async_client: AsyncClient):
    payload = {
        "name": "Queen Mira",
        "image_url": "https://example.com/portraits/mira.png",
    }
    resp = await async_client.post(
        "/v1/studio/avatars/build-mesh",
        json=payload,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_build_mesh_endpoint_validation_error(async_client: AsyncClient):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    payload = {
        "name": "",  # invalid: min_length=1
        "image_url": "https://example.com/portraits/mira.png",
    }
    resp = await async_client.post(
        "/v1/studio/avatars/build-mesh",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.fixture
def portrait_muse(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from app.integrations import image_gen_client, storage_client

    prompts: list[str] = []

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        prompts.append(prompt)
        return b"webp-bytes"

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        return f"https://storage.example/{object_key}"

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload)
    return prompts


@pytest.mark.asyncio
async def test_generate_portrait_returns_image_url(
    async_client: AsyncClient, portrait_muse: list[str]
):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    resp = await async_client.post(
        "/v1/studio/avatars/generate-portrait",
        json={"prompt": "Stern elven queen in silver armor"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["image_url"].startswith(
        "https://storage.example/leader-portraits/"
    )
    assert portrait_muse[0].startswith("Stern elven queen")


@pytest.mark.asyncio
async def test_generate_portrait_requires_auth(async_client: AsyncClient):
    resp = await async_client.post(
        "/v1/studio/avatars/generate-portrait", json={"prompt": "a queen"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_portrait_rejects_empty_prompt_422(
    async_client: AsyncClient, portrait_muse: list[str]
):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    resp = await async_client.post(
        "/v1/studio/avatars/generate-portrait",
        json={"prompt": "   "},
        headers=headers,
    )
    assert resp.status_code == 422
    assert portrait_muse == []


@pytest.mark.asyncio
async def test_list_premade_avatars_returns_the_library(async_client: AsyncClient):
    headers = {"x-dev-user-id": str(uuid.uuid4())}
    resp = await async_client.get("/v1/studio/avatars/premade", headers=headers)
    assert resp.status_code == 200
    avatars = resp.json()["avatars"]
    assert [avatar["id"] for avatar in avatars] == ["mira", "hana", "aldric", "isolde"]
    assert all(avatar["avatar_url"].endswith(".mavatar") for avatar in avatars)
    assert all(avatar["preview_url"].endswith(".webp") for avatar in avatars)
    assert avatars[0]["credit"] == "Miko © Yuki Shindo (AITuber OnAir)"
    assert avatars[1]["credit"] is None


@pytest.mark.asyncio
async def test_list_premade_avatars_requires_authentication(async_client: AsyncClient):
    resp = await async_client.get("/v1/studio/avatars/premade")
    assert resp.status_code == 401
