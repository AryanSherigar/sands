"""Service layer for voice input transcription."""

import uuid

from app.config import settings
from app.exceptions.voice_exceptions import AudioValidationError
from app.integrations import speech_client
from app.models.voice import TranscriptionResponse
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from sqlalchemy.ext.asyncio import AsyncSession


def _entity_names(entity: object) -> list[object]:
    if not isinstance(entity, dict):
        return []
    aliases = entity.get("aliases")
    alias_list = aliases if isinstance(aliases, list) else []
    return [entity.get("canonical_name"), *alias_list]


def build_phrase_hints(scenario_snapshot: dict[str, object]) -> list[str]:
    """Distinct entity names and aliases from a playthrough's pinned scenario,
    capped so the boost isn't diluted across a huge phrase list."""
    entities = scenario_snapshot.get("entities")
    raw_names = [
        name
        for entity in (entities if isinstance(entities, list) else [])
        for name in _entity_names(entity)
    ]
    hints = dict.fromkeys(
        name.strip()
        for name in raw_names
        if isinstance(name, str)
        and name.strip()
        and len(name.strip()) <= settings.speech_to_text_max_phrase_length
    )
    return list(hints)[: settings.speech_to_text_max_phrase_hints]


async def load_phrase_hints(
    playthrough_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> list[str]:
    """Phrase hints for a playthrough the user participates in; empty for an
    unknown playthrough or a non-participant, so hints never leak scenario
    content and never block transcription."""
    participants = await ParticipantRepo(session).list_by_playthrough(playthrough_id)
    if not any(participant.user_id == user_id for participant in participants):
        return []
    playthrough = await PlaythroughRepo(session).get_by_id(playthrough_id)
    if playthrough is None:
        return []
    return build_phrase_hints(playthrough.scenario_snapshot)


async def transcribe_turn_action_audio(
    content: bytes,
    content_type: str,
    phrase_hints: list[str] | None = None,
    quota: tuple[QuotaService, uuid.UUID] | None = None,
) -> TranscriptionResponse:
    if not content:
        raise AudioValidationError("No audio data received")
    if quota is None:
        return await _transcribe(content, content_type, phrase_hints)
    quota_service, user_id = quota
    async with quota_service.reserved(QuotaFeature.SPEECH_TO_TEXT, user_id):
        return await _transcribe(content, content_type, phrase_hints)


async def _transcribe(
    content: bytes, content_type: str, phrase_hints: list[str] | None
) -> TranscriptionResponse:
    transcript = await speech_client.transcribe_audio(
        content,
        content_type,
        settings.speech_to_text_timeout_seconds,
        phrase_hints=phrase_hints,
    )
    return TranscriptionResponse(transcript=transcript)
