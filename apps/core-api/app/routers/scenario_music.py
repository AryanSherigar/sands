"""FastAPI router for scenario mood-music endpoints."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.exceptions.music_exceptions import MusicValidationError
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.middleware.auth import get_current_user
from app.models.music import (
    MoodSlot,
    ScenarioMusicListResponse,
    ScenarioMusicResponse,
)
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.music_service import MAX_AUDIO_UPLOAD_BYTES, MusicService
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}/music",
    tags=["Scenario Music"],
)


def get_music_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> MusicService:
    return MusicService(scenario_music_repo=ScenarioMusicRepo(session))


def get_scenario_repo(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> ScenarioRepo:
    return ScenarioRepo(session)


async def _require_scenario_ownership(
    scenario_id: uuid.UUID, user: User, scenario_repo: ScenarioRepo
) -> None:
    """Every music endpoint operates on a scenario the caller must own."""
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise ScenarioNotFoundError()
    if scenario.creator_id != user.user_id:
        raise ScenarioAccessDeniedError()


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload's body, rejecting it as soon as it exceeds max_bytes."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise MusicValidationError("Audio file exceeds the 15MB size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("", response_model=ScenarioMusicListResponse)
async def list_scenario_music(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MusicService, Depends(get_music_service)],
    scenario_repo: Annotated[ScenarioRepo, Depends(get_scenario_repo)],
) -> ScenarioMusicListResponse:
    """List all 6 mood slots for a scenario."""
    await _require_scenario_ownership(scenario_id, user, scenario_repo)
    return await service.list_scenario_music(scenario_id)


@router.post("/{mood}/upload", response_model=ScenarioMusicResponse)
async def upload_music_track(
    scenario_id: uuid.UUID,
    mood: MoodSlot,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MusicService, Depends(get_music_service)],
    scenario_repo: Annotated[ScenarioRepo, Depends(get_scenario_repo)],
    file: Annotated[UploadFile, File()],
) -> ScenarioMusicResponse:
    """Upload a creator-supplied track for one mood slot."""
    await _require_scenario_ownership(scenario_id, user, scenario_repo)
    content = await _read_capped(file, MAX_AUDIO_UPLOAD_BYTES)
    return await service.upload_track(
        scenario_id, mood.value, content, file.content_type or ""
    )


@router.post("/{mood}/default", response_model=ScenarioMusicResponse)
async def set_default_track(
    scenario_id: uuid.UUID,
    mood: MoodSlot,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MusicService, Depends(get_music_service)],
    scenario_repo: Annotated[ScenarioRepo, Depends(get_scenario_repo)],
) -> ScenarioMusicResponse:
    """Explicitly select the built-in default track for a mood slot."""
    await _require_scenario_ownership(scenario_id, user, scenario_repo)
    return await service.set_default_track(scenario_id, mood.value)
