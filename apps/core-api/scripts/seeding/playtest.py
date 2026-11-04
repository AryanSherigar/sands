"""Creates a playtest playthrough through PlaythroughService, exactly as the
router does, so a generated scenario is proven playable and not only valid."""

import uuid

from app.models.playthrough import PlaythroughCreate, PlaythroughResponse
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
from sqlalchemy.ext.asyncio import AsyncSession


def build_playthrough_service(session: AsyncSession) -> PlaythroughService:
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


async def create_playtest(
    session: AsyncSession, user_id: uuid.UUID, data: PlaythroughCreate
) -> PlaythroughResponse:
    service = build_playthrough_service(session)
    return await service.create_playthrough(user_id, data, is_playtest=True)
