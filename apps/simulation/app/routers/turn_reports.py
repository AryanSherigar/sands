from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.api_turn import TurnReport
from app.models.auth import CurrentUser
from app.services.api_dependencies import get_turn_report_service
from app.services.turn_report_service import TurnReportService
from fastapi import APIRouter, Depends, Path

router = APIRouter(prefix="/v1/playthroughs/{playthrough_id}", tags=["turn-reports"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Reports = Annotated[TurnReportService, Depends(get_turn_report_service)]


@router.get("/turns/{turn}/report")
async def get_turn_report(
    playthrough_id: UUID, turn: Annotated[int, Path(ge=0)], user: User, service: Reports
) -> TurnReport:
    """Read what the player's faction recorded while the given turn resolved."""
    return await service.get_report(playthrough_id, user.user_id, turn)
