"""Internal router for service-to-service playthrough sync."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.middleware.internal_auth import require_internal_service_token
from app.models.playthrough import (
    PlaythroughOutcomeTextRequest,
    PlaythroughTurnSyncRequest,
    PlaythroughTurnSyncResponse,
)
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.invariant_repo import InvariantRepo
from app.repositories.map_repo import MapRepo
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.share_repo import ShareRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.services.playthrough_service import PlaythroughService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/internal/v1/playthroughs",
    tags=["internal"],
    dependencies=[Depends(require_internal_service_token)],
)


def get_playthrough_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> PlaythroughService:
    return PlaythroughService(
        playthrough_repo=PlaythroughRepo(session),
        participant_repo=ParticipantRepo(session),
        scenario_repo=ScenarioRepo(session),
        share_repo=ShareRepo(session),
        turn_log_repo=TurnLogRepo(session),
        entity_repo=EntityRepo(session),
        fact_repo=FactRepo(session),
        condition_repo=ConditionRepo(session),
        invariant_repo=InvariantRepo(session),
        end_condition_repo=EndConditionRepo(session),
        map_repo=MapRepo(session),
        minigame_repo=MinigameRepo(session),
        scenario_music_repo=ScenarioMusicRepo(session),
        memory_outbox_repo=MemoryOutboxRepo(session),
        user_repo=UserRepo(session),
    )


@router.patch("/{playthrough_id}/turn", response_model=PlaythroughTurnSyncResponse)
async def sync_turn_count(
    playthrough_id: uuid.UUID,
    data: PlaythroughTurnSyncRequest,
    service: Annotated[PlaythroughService, Depends(get_playthrough_service)],
) -> PlaythroughTurnSyncResponse:
    """Sync turn progression and status monotonically from external simulation."""
    return await service.sync_turn_count(playthrough_id=playthrough_id, data=data)


@router.patch(
    "/{playthrough_id}/outcome-text", response_model=PlaythroughTurnSyncResponse
)
async def set_outcome_text(
    playthrough_id: uuid.UUID,
    data: PlaythroughOutcomeTextRequest,
    service: Annotated[PlaythroughService, Depends(get_playthrough_service)],
) -> PlaythroughTurnSyncResponse:
    """Store the ending epilogue once the simulation has written it."""
    return await service.set_outcome_text(
        playthrough_id=playthrough_id, text=data.ended_outcome_text
    )
