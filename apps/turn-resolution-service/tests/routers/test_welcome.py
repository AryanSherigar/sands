import io
import json
import uuid
import wave

import httpx
import numpy as np
import pytest
import respx
from app.config import settings
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

FISH_URL = "https://api.fish.audio/v1/tts"


def speech_wave() -> bytes:
    samples = np.sin(np.arange(44100) * 2 * np.pi * 440 / 44100) * 0.2
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes((samples * 32767).astype("<i2").tobytes())
    return output.getvalue()


async def seed_run(session: AsyncSession, owner: uuid.UUID) -> Playthrough:
    session.add(User(user_id=owner, display_name="Owner", auth_provider_id=str(owner)))
    await session.flush()
    scenario = Scenario(
        creator_id=owner,
        title="Night Desk",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
    )
    session.add(scenario)
    await session.flush()
    run = Playthrough(
        scenario_id=scenario.scenario_id,
        created_by=owner,
        scenario_version=1,
        state={"setup": {"character_name": "Alex"}},
        scenario_snapshot={
            "world_data": {"presentation": {"welcome_tape_id": "tallis-v1"}}
        },
    )
    session.add(run)
    await session.flush()
    return run


async def test_welcome_requires_auth(async_client: httpx.AsyncClient) -> None:
    result = await async_client.post(f"/v1/voice/welcome/{uuid.uuid4()}")
    assert result.status_code == 401


@respx.mock
async def test_welcome_uses_persisted_name_in_alpha(
    async_client, db_session, monkeypatch
) -> None:
    owner = uuid.uuid4()
    run = await seed_run(db_session, owner)
    monkeypatch.setattr(settings, "fish_api_key", "test-key")
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    route = respx.post(FISH_URL).mock(
        return_value=httpx.Response(200, content=speech_wave())
    )
    result = await async_client.post(
        f"/v1/voice/welcome/{run.playthrough_id}", headers={"X-Dev-User-Id": str(owner)}
    )
    assert result.status_code == 200
    assert result.headers["content-type"] == "audio/wav"
    assert result.headers["cache-control"] == "no-store"
    payload = json.loads(route.calls[0].request.content)
    assert payload["text"] == "Thank you for your service, Alex."
    assert payload["reference_id"] == settings.fish_katie_voice_id
    assert result.content.startswith(b"RIFF")


@pytest.mark.parametrize(
    "case,status",
    [("owner", 404), ("turn", 400), ("ended", 400), ("marker", 400), ("tags", 400)],
)
@respx.mock
async def test_welcome_rejects_ineligible_run(
    async_client, db_session, case, status
) -> None:
    owner = uuid.uuid4()
    run = await seed_run(db_session, owner)
    if case == "owner":
        owner = uuid.uuid4()
    if case == "turn":
        run.turn_count = 1
    if case == "ended":
        run.status = "completed"
    if case == "marker":
        run.scenario_snapshot = {}
    if case == "tags":
        run.state = {"setup": {"character_name": "[whispering] Alex"}}
    await db_session.flush()
    route = respx.post(FISH_URL).mock(return_value=httpx.Response(500))
    result = await async_client.post(
        f"/v1/voice/welcome/{run.playthrough_id}", headers={"X-Dev-User-Id": str(owner)}
    )
    assert result.status_code == status
    assert not route.called


@respx.mock
async def test_welcome_provider_failure_is_not_retried(
    async_client, db_session, monkeypatch
) -> None:
    owner = uuid.uuid4()
    run = await seed_run(db_session, owner)
    monkeypatch.setattr(settings, "fish_api_key", "test-key")
    route = respx.post(FISH_URL).mock(return_value=httpx.Response(402))
    result = await async_client.post(
        f"/v1/voice/welcome/{run.playthrough_id}", headers={"X-Dev-User-Id": str(owner)}
    )
    assert result.status_code == 502
    assert route.call_count == 1
