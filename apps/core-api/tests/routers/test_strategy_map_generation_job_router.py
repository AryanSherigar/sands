"""Integration tests for the background strategy map generation job endpoints."""

import uuid
from io import BytesIO

import httpx
import pytest
from app.exceptions.upload_exceptions import ImageGenerationError
from app.integrations import image_gen_client, storage_client
from app.repositories.map_generation_job_repo import MapGenerationJobRepo
from app.repositories.user_repo import UserRepo
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.scenario import StrategyScenario

REGION_SIZE = (1792, 1344)
EDIT_SIZE = (1824, 1376)
DESCRIPTION = "A river kingdom split by marsh and hills"


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
async def scenario_id(
    async_client_real_background: httpx.AsyncClient,
    headers,
    cleanup_scenarios: list[uuid.UUID],
) -> str:
    response = await async_client_real_background.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "strategy_document": StrategyScenario().model_dump(mode="json"),
        },
        headers=headers,
    )
    assert response.status_code == 201
    cleanup_scenarios.append(uuid.UUID(response.json()["scenario_id"]))
    return response.json()["scenario_id"]


@pytest.fixture
def fake_muse(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    behaviour = {"should_fail_region": False, "should_fail_art": False}

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        if behaviour["should_fail_region"]:
            raise ImageGenerationError("Image generation is temporarily unavailable")
        return _image_bytes(REGION_SIZE, "WEBP")

    async def fake_edit(
        prompt: str, image_bytes: bytes, content_type: str, timeout_seconds: int
    ) -> bytes:
        if behaviour["should_fail_art"]:
            raise ImageGenerationError("Image generation is temporarily unavailable")
        return _image_bytes(EDIT_SIZE, "WEBP")

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        return f"https://storage.example/{object_key}"

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(image_gen_client, "edit_image", fake_edit)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload)
    return behaviour


def _generate_path(scenario_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-map/generate"


def _jobs_path(scenario_id: str, job_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-map/jobs/{job_id}"


async def test_generate_returns_202_and_job_completes_with_art(
    async_client_real_background, headers, scenario_id, fake_muse
) -> None:
    response = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    polled = await async_client_real_background.get(
        _jobs_path(scenario_id, response.json()["job_id"]), headers=headers
    )
    job = polled.json()
    assert job["status"] == "succeeded"
    assert job["has_art"] is True
    assert job["region_image_url"].startswith("https://storage.example/")
    assert job["picture_url"].endswith(".webp")
    assert (job["width"], job["height"]) == REGION_SIZE


async def test_failed_art_step_still_succeeds_with_the_region_image(
    async_client_real_background, headers, scenario_id, fake_muse
) -> None:
    fake_muse["should_fail_art"] = True

    response = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )

    polled = await async_client_real_background.get(
        _jobs_path(scenario_id, response.json()["job_id"]), headers=headers
    )
    job = polled.json()
    assert job["status"] == "succeeded"
    assert job["has_art"] is False
    assert job["picture_url"] is None
    assert job["region_image_url"] is not None


async def test_failed_region_step_marks_the_job_failed(
    async_client_real_background, headers, scenario_id, fake_muse
) -> None:
    fake_muse["should_fail_region"] = True

    response = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )

    polled = await async_client_real_background.get(
        _jobs_path(scenario_id, response.json()["job_id"]), headers=headers
    )
    job = polled.json()
    assert job["status"] == "failed"
    assert job["error_message"]
    assert job["region_image_url"] is None


async def test_generate_while_a_job_is_running_returns_that_job(
    async_client_real_background, db_session, dev_user, headers, scenario_id, fake_muse
) -> None:
    running = await MapGenerationJobRepo(db_session).create(
        uuid.UUID(scenario_id), dev_user.user_id, DESCRIPTION
    )
    await MapGenerationJobRepo(db_session).mark_running(running.job_id)
    await db_session.commit()

    response = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == str(running.job_id)
    assert response.json()["status"] == "running"


async def test_latest_job_is_404_until_one_exists_then_resumes_it(
    async_client_real_background, headers, scenario_id, fake_muse
) -> None:
    latest_path = f"/v1/scenarios/{scenario_id}/strategy-map/jobs/latest"
    before = await async_client_real_background.get(latest_path, headers=headers)
    started = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )

    after = await async_client_real_background.get(latest_path, headers=headers)

    assert before.status_code == 404
    assert after.status_code == 200
    assert after.json()["job_id"] == started.json()["job_id"]


async def test_another_creator_cannot_poll_the_job(
    async_client_real_background, db_session, headers, scenario_id, fake_muse
) -> None:
    started = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": DESCRIPTION}, headers=headers
    )
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )
    await db_session.commit()

    response = await async_client_real_background.get(
        _jobs_path(scenario_id, started.json()["job_id"]),
        headers={"x-dev-user-id": str(stranger.user_id)},
    )

    assert response.status_code in (403, 404)


async def test_generate_rejects_a_too_short_description(
    async_client_real_background, headers, scenario_id, fake_muse
) -> None:
    response = await async_client_real_background.post(
        _generate_path(scenario_id), json={"description": "ab"}, headers=headers
    )

    assert response.status_code == 422
