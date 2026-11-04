"""Integration tests for the strategy map generation endpoints, Muse faked."""

import uuid
from io import BytesIO

import pytest
from app.config import settings
from app.exceptions.upload_exceptions import ImageGenerationError
from app.integrations import image_gen_client, storage_client
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.scenario import StrategyScenario

REGION_SIZE = (1792, 1344)
EDIT_SIZE = (1824, 1376)


def _image_bytes(size: tuple[int, int], image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (40, 120, 200)).save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
def headers(dev_user):
    return {"x-dev-user-id": str(dev_user.user_id)}


@pytest.fixture
async def scenario_id(async_client: AsyncClient, headers) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "strategy_document": StrategyScenario().model_dump(mode="json"),
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["scenario_id"]


@pytest.fixture
def muse_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        calls.append("generate")
        return _image_bytes(REGION_SIZE, "WEBP")

    async def fake_edit(
        prompt: str, image_bytes: bytes, content_type: str, timeout_seconds: int
    ) -> bytes:
        calls.append("edit")
        return _image_bytes(EDIT_SIZE, "WEBP")

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        return f"https://storage.example/{object_key}"

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(image_gen_client, "edit_image", fake_edit)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload)
    return calls


def _regions_path(scenario_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-map/generate-regions"


def _art_path(scenario_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-map/generate-art"


async def test_generate_regions_returns_url_and_size(
    async_client: AsyncClient, headers, scenario_id, muse_calls
) -> None:
    response = await async_client.post(
        _regions_path(scenario_id),
        json={"description": "a frozen northern realm"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["width"], body["height"]) == REGION_SIZE
    assert body["region_image_url"].startswith("https://storage.example/scenario-maps/")
    assert muse_calls == ["generate"]


@pytest.mark.parametrize("description", ["   ", "ab", "x" * 501])
async def test_generate_regions_rejects_invalid_description(
    async_client: AsyncClient, headers, scenario_id, muse_calls, description
) -> None:
    response = await async_client.post(
        _regions_path(scenario_id), json={"description": description}, headers=headers
    )

    assert response.status_code == 422
    assert muse_calls == []


async def test_generate_regions_muse_failure_returns_502_and_refunds_quota(
    async_client: AsyncClient,
    headers,
    scenario_id,
    muse_calls,
    rate_limit_enabled,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def failing_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        nonlocal attempts
        attempts += 1
        raise ImageGenerationError()

    monkeypatch.setattr(image_gen_client, "generate_image", failing_generate)
    monkeypatch.setattr(settings, "quota_cover_image_per_user", 2)

    statuses = [
        (
            await async_client.post(
                _regions_path(scenario_id),
                json={"description": "a desert empire"},
                headers=headers,
            )
        ).status_code
        for _ in range(4)
    ]

    assert statuses == [502, 502, 502, 502]
    assert attempts == 4


async def test_generate_regions_quota_exhausted_returns_429_without_calling_muse(
    async_client: AsyncClient,
    headers,
    scenario_id,
    muse_calls,
    rate_limit_enabled,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "quota_cover_image_per_user", 0)

    response = await async_client.post(
        _regions_path(scenario_id),
        json={"description": "a desert empire"},
        headers=headers,
    )

    assert response.status_code == 429
    assert muse_calls == []


async def test_generate_art_returns_picture_url_at_region_size(
    async_client: AsyncClient, headers, scenario_id, muse_calls
) -> None:
    response = await async_client.post(
        _art_path(scenario_id),
        data={"description": "a desert empire"},
        files={"file": ("regions.png", _image_bytes(REGION_SIZE, "PNG"), "image/png")},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["width"], body["height"]) == REGION_SIZE
    assert body["picture_url"].endswith(".webp")
    assert muse_calls == ["edit"]


async def test_generate_art_rejects_spoofed_png(
    async_client: AsyncClient, headers, scenario_id, muse_calls
) -> None:
    response = await async_client.post(
        _art_path(scenario_id),
        data={"description": "a desert empire"},
        files={"file": ("regions.png", b"RIFF0000WEBPdata", "image/png")},
        headers=headers,
    )

    assert response.status_code == 400
    assert muse_calls == []


async def test_generate_art_rejects_oversized_upload(
    async_client: AsyncClient, headers, scenario_id, muse_calls
) -> None:
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 1)

    response = await async_client.post(
        _art_path(scenario_id),
        data={"description": "a desert empire"},
        files={"file": ("regions.png", oversized, "image/png")},
        headers=headers,
    )

    assert response.status_code == 400
    assert muse_calls == []


async def test_generate_regions_rejects_a_scenario_the_user_does_not_own(
    async_client: AsyncClient, db_session, scenario_id, muse_calls
) -> None:
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    response = await async_client.post(
        _regions_path(scenario_id),
        json={"description": "a frozen northern realm"},
        headers={"x-dev-user-id": str(stranger.user_id)},
    )

    assert response.status_code == 403
    assert muse_calls == []


async def test_generate_regions_rejects_an_unknown_scenario(
    async_client: AsyncClient, headers, muse_calls
) -> None:
    response = await async_client.post(
        _regions_path(str(uuid.uuid4())),
        json={"description": "a frozen northern realm"},
        headers=headers,
    )

    assert response.status_code == 404
    assert muse_calls == []
