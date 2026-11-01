"""Integration tests for voice transcription endpoint POST /v1/voice/transcribe."""

import uuid

from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.voice_exceptions import TranscriptionUnavailableError
from app.integrations import speech_client
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _make_auth_headers() -> dict[str, str]:
    return {"X-Dev-User-Id": str(uuid.uuid4())}


def _audio_file(content_type: str = "audio/webm", size: int = 32) -> dict:
    return {"file": ("action.webm", b"x" * size, content_type)}


async def test_transcribe_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post("/v1/voice/transcribe", files=_audio_file())
    assert response.status_code == 401


async def test_transcribe_returns_transcript_json(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_transcribe_audio(
        content, content_type, timeout_seconds, phrase_hints=None
    ):
        return "I search the room"

    monkeypatch.setattr(speech_client, "transcribe_audio", fake_transcribe_audio)

    response = await async_client.post(
        "/v1/voice/transcribe",
        files=_audio_file(),
        headers=_make_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": "I search the room"}


async def test_transcribe_rejects_oversized_upload(async_client: AsyncClient) -> None:
    oversized = settings.voice_input_max_audio_bytes + 1

    response = await async_client.post(
        "/v1/voice/transcribe",
        files=_audio_file(size=oversized),
        headers=_make_auth_headers(),
    )

    assert response.status_code == 400


async def test_transcribe_upstream_unavailable_returns_502(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def failing_transcribe_audio(
        content, content_type, timeout_seconds, phrase_hints=None
    ):
        raise TranscriptionUnavailableError()

    monkeypatch.setattr(speech_client, "transcribe_audio", failing_transcribe_audio)

    response = await async_client.post(
        "/v1/voice/transcribe",
        files=_audio_file(),
        headers=_make_auth_headers(),
    )

    assert response.status_code == 502


async def _seed_playthrough(
    session: AsyncSession, user_id: uuid.UUID, is_participant: bool
) -> uuid.UUID:
    owner_id, scenario_id = (user_id if is_participant else uuid.uuid4()), uuid.uuid4()
    session.add(
        User(user_id=owner_id, display_name="Owner", auth_provider_id=str(owner_id))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=owner_id,
            title="Test Scenario",
            mode="master",
            complexity_tier="master",
            player_count_support="both",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=owner_id,
        scenario_version=1,
        scenario_snapshot={
            "entities": [
                {"canonical_name": "Zhaerith", "aliases": ["the Pale Warden"]},
            ]
        },
    )
    session.add(playthrough)
    await session.flush()
    session.add(
        Participant(
            playthrough_id=playthrough.playthrough_id,
            user_id=owner_id,
            role="owner",
            turn_order_position=1,
        )
    )
    await session.flush()
    return playthrough.playthrough_id


async def _post_with_playthrough(
    async_client: AsyncClient,
    monkeypatch,
    db_session: AsyncSession,
    is_participant: bool,
) -> list[str] | None:
    captured: dict[str, list[str] | None] = {}

    async def fake_transcribe_audio(
        content, content_type, timeout_seconds, phrase_hints=None
    ):
        captured["phrase_hints"] = phrase_hints
        return "ok"

    monkeypatch.setattr(speech_client, "transcribe_audio", fake_transcribe_audio)
    user_id = uuid.uuid4()
    playthrough_id = await _seed_playthrough(db_session, user_id, is_participant)

    response = await async_client.post(
        "/v1/voice/transcribe",
        files=_audio_file(),
        data={"playthrough_id": str(playthrough_id)},
        headers={"X-Dev-User-Id": str(user_id)},
    )

    assert response.status_code == 200
    return captured["phrase_hints"]


async def test_transcribe_passes_entity_names_as_phrase_hints(
    async_client: AsyncClient, monkeypatch, db_session: AsyncSession
) -> None:
    hints = await _post_with_playthrough(async_client, monkeypatch, db_session, True)

    assert hints == ["Zhaerith", "the Pale Warden"]


async def test_transcribe_omits_phrase_hints_for_non_participant(
    async_client: AsyncClient, monkeypatch, db_session: AsyncSession
) -> None:
    hints = await _post_with_playthrough(async_client, monkeypatch, db_session, False)

    assert hints == []


async def test_transcribe_daily_quota_returns_429(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    async def fake_transcribe_audio(
        content, content_type, timeout_seconds, phrase_hints=None
    ):
        return "I search the room"

    monkeypatch.setattr(speech_client, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(settings, "quota_speech_to_text_per_user", 1)
    headers = _make_auth_headers()

    first = await async_client.post(
        "/v1/voice/transcribe", files=_audio_file(), headers=headers
    )
    second = await async_client.post(
        "/v1/voice/transcribe", files=_audio_file(), headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "quota_exceeded"
    assert second.json()["scope"] == "speech_to_text"
