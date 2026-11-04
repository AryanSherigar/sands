"""Scenario music domain service: uploads and default track selection."""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, datetime

from app.db.models.scenario_music import MOOD_SLOTS, ScenarioMusic
from app.exceptions.music_exceptions import MusicValidationError
from app.integrations import storage_client
from app.models.music import ScenarioMusicListResponse, ScenarioMusicResponse
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.services import default_music
from mutagen import MutagenError
from mutagen._file import File as MutagenFile

MAX_AUDIO_UPLOAD_BYTES = 15 * 1024 * 1024
MIN_TRACK_DURATION_SECONDS = 30

ALLOWED_AUDIO_CONTENT_TYPES: dict[str, str] = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
}

_SCENARIO_MUSIC_PREFIX = "scenario-music"


class MusicService:
    """Service handling scenario music slot assignment."""

    def __init__(
        self,
        scenario_music_repo: ScenarioMusicRepo,
    ) -> None:
        self.scenario_music_repo = scenario_music_repo

    async def list_scenario_music(
        self, scenario_id: uuid.UUID
    ) -> ScenarioMusicListResponse:
        """Return all 6 mood slots, synthesizing 'default' for unset ones."""
        rows = await self.scenario_music_repo.get_by_scenario(scenario_id)
        rows_by_mood = {row.mood: row for row in rows}
        items = [
            _to_response(rows_by_mood[mood])
            if mood in rows_by_mood
            else _synthesize_default(scenario_id, mood)
            for mood in MOOD_SLOTS
        ]
        return ScenarioMusicListResponse(items=items)

    async def upload_track(
        self,
        scenario_id: uuid.UUID,
        mood: str,
        content: bytes,
        content_type: str,
    ) -> ScenarioMusicResponse:
        """Validate and upload a creator-supplied track, assigning it to a mood slot."""
        extension = ALLOWED_AUDIO_CONTENT_TYPES.get(content_type)
        if extension is None:
            raise MusicValidationError(
                "Unsupported audio format. Allowed: MP3, WAV, OGG."
            )
        if len(content) > MAX_AUDIO_UPLOAD_BYTES:
            raise MusicValidationError("Audio file exceeds the 15MB size limit.")

        duration_seconds = await _probe_duration(content)
        if duration_seconds < MIN_TRACK_DURATION_SECONDS:
            raise MusicValidationError(
                f"Track duration must be at least {MIN_TRACK_DURATION_SECONDS} "
                f"seconds, got {duration_seconds:.1f}."
            )

        object_key = f"{_SCENARIO_MUSIC_PREFIX}/{uuid.uuid4()}{extension}"
        track_url = await storage_client.upload_image(content, content_type, object_key)

        row = await self.scenario_music_repo.upsert(
            scenario_id=scenario_id,
            mood=mood,
            source="upload",
            track_url=track_url,
            duration_seconds=duration_seconds,
        )
        return ScenarioMusicResponse.model_validate(row)

    async def set_default_track(
        self, scenario_id: uuid.UUID, mood: str
    ) -> ScenarioMusicResponse:
        """Explicitly select the built-in default track for a mood slot."""
        row = await self.scenario_music_repo.upsert(
            scenario_id=scenario_id, mood=mood, source="default", track_url=None
        )
        return _to_response(row)


def _to_response(row: ScenarioMusic) -> ScenarioMusicResponse:
    """Build a response for a persisted row, resolving the real playable
    default-track URL for 'default'-source rows (DB keeps track_url=NULL for
    those, so a future default-asset swap needs no per-scenario migration)."""
    response = ScenarioMusicResponse.model_validate(row)
    if response.source == "default":
        response = response.model_copy(
            update={"track_url": default_music.default_track_url(row.mood)}
        )
    return response


def _synthesize_default(scenario_id: uuid.UUID, mood: str) -> ScenarioMusicResponse:
    """Build an unpersisted 'default' response for a mood slot with no row."""
    now = datetime.now(UTC)
    return ScenarioMusicResponse(
        scenario_music_id=uuid.uuid4(),
        scenario_id=scenario_id,
        mood=mood,
        source="default",
        track_url=default_music.default_track_url(mood),
        created_at=now,
        updated_at=now,
    )


async def _probe_duration(content: bytes) -> float:
    """Read an audio file's duration from its header, without full decoding."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _probe_duration_sync, content)
    except MutagenError as exc:
        raise MusicValidationError(f"Could not read audio file: {exc}") from exc


def _probe_duration_sync(content: bytes) -> float:
    audio = MutagenFile(io.BytesIO(content))
    if audio is None or audio.info is None or audio.info.length <= 0:
        raise MusicValidationError("Could not determine audio track duration.")
    return float(audio.info.length)
