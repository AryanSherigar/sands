from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.api_battle import BattlePage, ExchangeReportPage
from app.models.api_battle_speech import SpeechTalkRequest, SpeechTalkResult, SpeechView
from app.models.auth import CurrentUser
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.world_battle import BattleView
from app.services.api_dependencies import (
    get_battle_service,
    get_battle_speech_service,
    get_campaign_service,
)
from app.services.battle_service import BattleService
from app.services.battle_speech_service import BattleSpeechService
from app.services.campaign_service import CampaignService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/v1/playthroughs/{playthrough_id}/battles", tags=["battles"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Battles = Annotated[BattleService, Depends(get_battle_service)]
Speeches = Annotated[BattleSpeechService, Depends(get_battle_speech_service)]
Campaign = Annotated[CampaignService, Depends(get_campaign_service)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("")
async def list_battles(
    playthrough_id: UUID,
    user: User,
    service: Battles,
    after_id: Annotated[str, Query(max_length=256)] = "",
    limit: Limit = 50,
) -> BattlePage:
    """List observed battles, active first, with a version-scoped cursor."""
    return await service.list_battles(playthrough_id, user.user_id, after_id, limit)


@router.post("/advance")
async def advance_campaign(
    playthrough_id: UUID,
    request: OperationGuard,
    user: User,
    service: Campaign,
) -> MutationResponse:
    """Resolve one global wave without spending a command point."""
    return await service.advance(playthrough_id, user.user_id, request)


@router.get("/{battle_id}")
async def get_battle(
    playthrough_id: UUID,
    battle_id: str,
    user: User,
    service: Battles,
) -> BattleView:
    """Read exact own data and allowlisted opponent observations."""
    return await service.load_battle(playthrough_id, user.user_id, battle_id)


@router.get("/{battle_id}/speech")
async def get_battle_speech(
    playthrough_id: UUID,
    battle_id: str,
    user: User,
    service: Speeches,
) -> SpeechView:
    """Read the officer's report, the army's mood and the speech so far."""
    return await service.get_view(playthrough_id, user.user_id, battle_id)


@router.post("/{battle_id}/speech/talks")
async def submit_speech_talk(
    playthrough_id: UUID,
    battle_id: str,
    request: SpeechTalkRequest,
    user: User,
    service: Speeches,
) -> SpeechTalkResult:
    """Give the next of three talks; the third grades the whole speech and moves morale."""
    return await service.submit_talk(playthrough_id, user.user_id, battle_id, request)


@router.post("/{battle_id}/speech/skip")
async def skip_battle_speech(
    playthrough_id: UUID,
    battle_id: str,
    request: OperationGuard,
    user: User,
    service: Speeches,
) -> SpeechTalkResult:
    """Skip the speech with no morale change."""
    return await service.skip(playthrough_id, user.user_id, battle_id, request)


@router.get("/{battle_id}/reports")
async def list_reports(
    playthrough_id: UUID,
    battle_id: str,
    user: User,
    service: Battles,
    after_exchange: Annotated[int, Query(ge=0)] = 0,
    limit: Limit = 50,
) -> ExchangeReportPage:
    """List redacted exchange reports by monotonic total exchange ordinal."""
    return await service.list_reports(
        playthrough_id, user.user_id, battle_id, after_exchange, limit
    )
