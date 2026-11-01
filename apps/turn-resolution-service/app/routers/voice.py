"""FastAPI router for the voice-input transcription endpoint.

Non-SSE, request/response only. Deliberately not part of app/turn/pipeline.py
or app/turn/steps/ -- transcription happens before turn submission, so it
never touches the turn-latency SLA in
docs/specs/master-mode-turn-pipeline.spec.md.
"""

import uuid
from typing import Annotated

from app.config import settings
from app.db.connection import get_db_session
from app.exceptions.voice_exceptions import AudioValidationError
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.voice import TranscriptionResponse
from app.routers.alpha_guards import forbid_in_alpha_mode
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.voice_service import load_phrase_hints, transcribe_turn_action_audio
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/voice",
    tags=["Voice"],
    dependencies=[Depends(forbid_in_alpha_mode)],
)


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload's body, rejecting it as soon as it exceeds max_bytes."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise AudioValidationError(
                f"Recording exceeds the {max_bytes // (1024 * 1024)}MB limit."
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_action_audio(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
    file: Annotated[UploadFile, File()],
    playthrough_id: Annotated[uuid.UUID | None, Form()] = None,
) -> TranscriptionResponse:
    """Transcribe a short player-recorded action clip to text for review.

    When playthrough_id is given and the caller participates in it, the
    scenario's entity names bias recognition toward the right spellings.
    """
    content = await _read_capped(file, settings.voice_input_max_audio_bytes)
    phrase_hints: list[str] = []
    if playthrough_id is not None:
        phrase_hints = await load_phrase_hints(
            playthrough_id, current_user.user_id, session
        )
    return await transcribe_turn_action_audio(
        content,
        file.content_type or "",
        phrase_hints,
        quota=(quota_service, current_user.user_id),
    )
