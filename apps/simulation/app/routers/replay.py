from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.api_replay import HistoricalWorldResponse, ReplayVerificationResponse
from app.models.auth import CurrentUser
from app.services.api_dependencies import get_replay_service
from app.services.replay_service import ReplayService
from fastapi import APIRouter, Depends, Path, Query

router = APIRouter(prefix="/v1/playthroughs/{playthrough_id}", tags=["replay"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Replay = Annotated[ReplayService, Depends(get_replay_service)]


@router.get("/history/{turn}")
async def get_history(
    playthrough_id: UUID, turn: Annotated[int, Path(ge=0)], user: User, service: Replay
) -> HistoricalWorldResponse:
    """Read an immutable, observer-safe completed-turn projection."""
    return await service.load_history(playthrough_id, user.user_id, turn)


@router.post("/replay/verify")
async def verify_replay(
    playthrough_id: UUID,
    user: User,
    service: Replay,
    through_turn: Annotated[int | None, Query(ge=0)] = None,
) -> ReplayVerificationResponse:
    """Reconstruct recorded history without mutating live simulation state."""
    return await service.verify(playthrough_id, user.user_id, through_turn)
