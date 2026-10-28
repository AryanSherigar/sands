"""Scenario music domain service: uploads, defaults, and Lyria generation jobs."""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, datetime

import structlog
from app.config import settings
from app.db.models.scenario_music import MOOD_SLOTS, ScenarioMusic
from app.db.models.user import User
from app.exceptions.music_exceptions import (
    MusicJobNotFoundError,
    MusicValidationError,
)
from app.exceptions.rate_limit_exceptions import (
    CODE_QUOTA_EXCEEDED,
    RateLimitExceededError,
)
from app.integrations import music_gen_client, storage_client
from app.models.music import (
    MusicGenerationJobResponse,
    MusicGenerationRequest,
    QuotaStatusResponse,
    ScenarioMusicListResponse,
    ScenarioMusicResponse,
)
from app.repositories.music_generation_job_repo import MusicGenerationJobRepo
from app.repositories.music_generation_log_repo import MusicGenerationLogRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.services import default_music
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, quota_scope
from mutagen import MutagenError
from mutagen._file import File as MutagenFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger()

MAX_AUDIO_UPLOAD_BYTES = 15 * 1024 * 1024
MIN_TRACK_DURATION_SECONDS = 30
MAX_GENERATIONS_PER_SCENARIO = 20
SCENARIO_GENERATION_LIMIT_SCOPE = "music_generation_scenario"

ALLOWED_AUDIO_CONTENT_TYPES: dict[str, str] = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
}

_SCENARIO_MUSIC_PREFIX = "scenario-music"
_MUSIC_PREVIEW_PREFIX = "music-previews"
_GENERATED_TRACK_CONTENT_TYPE = "audio/wav"

EVENT_MUSIC_GENERATION_JOB_SUCCEEDED = "music_generation_job_succeeded"
EVENT_MUSIC_GENERATION_JOB_FAILED = "music_generation_job_failed"


class MusicService:
    """Service handling scenario music slot assignment and Lyria job orchestration."""

    def __init__(
        self,
        scenario_music_repo: ScenarioMusicRepo,
        job_repo: MusicGenerationJobRepo,
        log_repo: MusicGenerationLogRepo,
        quota_service: QuotaService | None = None,
    ) -> None:
        self.scenario_music_repo = scenario_music_repo
        self.job_repo = job_repo
        self.log_repo = log_repo
        self.quota_service = quota_service

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

    async def request_generation(
        self,
        scenario_id: uuid.UUID,
        creator: User,
        request: MusicGenerationRequest,
    ) -> MusicGenerationJobResponse:
        """Check quotas, log the attempt, and create a pending generation job.

        Wrapped in a per-creator Postgres advisory lock (released at this
        request's transaction commit) so two concurrent requests from the
        same creator can't both pass the per-scenario check before either
        logs its attempt. The daily per-creator quota is atomic on its own.
        """
        await self.log_repo.acquire_creator_generation_lock(creator.user_id)
        await self._check_scenario_quota(scenario_id)
        async with quota_scope(
            self.quota_service, QuotaFeature.MUSIC_GENERATION, creator
        ):
            await self.log_repo.create(scenario_id, creator.user_id)
            job = await self.job_repo.create(
                scenario_id=scenario_id,
                creator_id=creator.user_id,
                mood=request.mood.value,
                prompt=request.prompt,
            )
        return MusicGenerationJobResponse.model_validate(job)

    @staticmethod
    async def run_generation_job(
        job_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession],
        quota_service: QuotaService | None = None,
    ) -> None:
        """Run the Lyria call in the background against its own DB session."""
        async with session_factory() as session:
            job_repo = MusicGenerationJobRepo(session)
            job = await job_repo.get_by_id(job_id)
            if job is None:
                return
            creator_id, requested_at = job.creator_id, job.created_at

            await job_repo.mark_running(job_id)
            try:
                audio_bytes, metadata = await music_gen_client.generate_music(
                    prompt=job.prompt,
                    mood=job.mood,
                    timeout_seconds=60,
                )
                actual_duration_seconds = await _probe_duration(audio_bytes)
                object_key = f"{_MUSIC_PREVIEW_PREFIX}/{uuid.uuid4()}.wav"
                preview_url = await storage_client.upload_image(
                    audio_bytes, _GENERATED_TRACK_CONTENT_TYPE, object_key
                )
            # NOTE: Intentionally broad. This is the terminal handler for the
            # background music-generation job -- there is no other error path
            # once we reach here, and narrowing risks an unanticipated
            # exception type propagating unhandled, leaving the job stuck in
            # "running" status forever instead of being marked failed with a
            # visible error message.
            except Exception as exc:  # noqa: BLE001 - captured as job error_message
                await job_repo.mark_failed(job_id, str(exc))
                logger.warning(
                    EVENT_MUSIC_GENERATION_JOB_FAILED,
                    job_id=str(job_id),
                    error=str(exc),
                )
                await session.commit()
                if quota_service is not None:
                    await quota_service.refund_for(
                        QuotaFeature.MUSIC_GENERATION, creator_id, requested_at
                    )
                return

            await job_repo.mark_succeeded(
                job_id,
                preview_url=preview_url,
                key=metadata.key,
                bpm=metadata.bpm,
                duration_seconds=actual_duration_seconds,
            )
            logger.info(EVENT_MUSIC_GENERATION_JOB_SUCCEEDED, job_id=str(job_id))
            await session.commit()

    async def get_job_status(
        self, job_id: uuid.UUID, creator_id: uuid.UUID
    ) -> MusicGenerationJobResponse:
        """Poll a generation job's status, scoped to its owning creator."""
        job = await self.job_repo.get_by_id(job_id)
        if job is None or job.creator_id != creator_id:
            raise MusicJobNotFoundError()
        return MusicGenerationJobResponse.model_validate(job)

    async def confirm_generated_track(
        self, scenario_id: uuid.UUID, job_id: uuid.UUID, creator_id: uuid.UUID
    ) -> ScenarioMusicResponse:
        """Commit a succeeded job's preview track to its mood slot."""
        job = await self.job_repo.get_by_id(job_id)
        if (
            job is None
            or job.creator_id != creator_id
            or job.scenario_id != scenario_id
            or job.status != "succeeded"
        ):
            raise MusicJobNotFoundError()

        row = await self.scenario_music_repo.upsert(
            scenario_id=scenario_id,
            mood=job.mood,
            source="generated",
            track_url=job.preview_url,
            generation_prompt=job.prompt,
            key=job.key,
            bpm=job.bpm,
            duration_seconds=job.duration_seconds,
        )
        return ScenarioMusicResponse.model_validate(row)

    async def discard_job(self, job_id: uuid.UUID, creator_id: uuid.UUID) -> None:
        """Discard a generation job without assigning it to any slot.

        No-op on scenario_music: the attempt was already counted against
        quota at request_generation time, so discarding gives no free re-roll.
        """
        job = await self.job_repo.get_by_id(job_id)
        if job is None or job.creator_id != creator_id:
            raise MusicJobNotFoundError()

    async def get_quota_status(
        self, scenario_id: uuid.UUID, creator_id: uuid.UUID
    ) -> QuotaStatusResponse:
        """Report current generation-quota usage."""
        scenario_used = await self.log_repo.count_by_scenario(scenario_id)
        return QuotaStatusResponse(
            scenario_generations_used=scenario_used,
            scenario_generations_limit=MAX_GENERATIONS_PER_SCENARIO,
            creator_generations_used_today=await self._creator_used_today(creator_id),
            creator_generations_limit_per_day=settings.quota_music_generation_per_user,
        )

    async def _creator_used_today(self, creator_id: uuid.UUID) -> int:
        if self.quota_service is not None:
            return await self.quota_service.used_today(
                QuotaFeature.MUSIC_GENERATION, creator_id
            )
        utc_midnight = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return await self.log_repo.count_by_creator_since(creator_id, utc_midnight)

    async def _check_scenario_quota(self, scenario_id: uuid.UUID) -> None:
        """The per-scenario lifetime cap is a product rule, not a rate limit."""
        scenario_used = await self.log_repo.count_by_scenario(scenario_id)
        if scenario_used >= MAX_GENERATIONS_PER_SCENARIO:
            raise RateLimitExceededError(
                "This scenario has reached its music generation limit.",
                code=CODE_QUOTA_EXCEEDED,
                scope=SCENARIO_GENERATION_LIMIT_SCOPE,
                reset_at=None,
                retry_after_seconds=None,
            )


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
