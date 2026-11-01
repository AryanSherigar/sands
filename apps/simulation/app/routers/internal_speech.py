from typing import Annotated
from uuid import UUID

from app.middleware.internal_auth import require_internal_service_token
from app.models.speech_grading import SpeechGradeRequest
from app.services.api_dependencies import get_speech_grade_service
from app.services.speech_grade_service import SpeechGradeService
from fastapi import APIRouter, Depends, Header
from strategy_contracts.scene import BattleSpeechOutcome

HEADER_ACTING_USER_ID = "X-Acting-User-Id"

router = APIRouter(
    prefix="/internal/v1/playthroughs",
    tags=["internal"],
    dependencies=[Depends(require_internal_service_token)],
)
ActingUser = Annotated[UUID, Header(alias=HEADER_ACTING_USER_ID)]
Grader = Annotated[SpeechGradeService, Depends(get_speech_grade_service)]


@router.post("/{playthrough_id}/battle-speech/grade")
async def grade_battle_speech(
    playthrough_id: UUID,
    request: SpeechGradeRequest,
    acting_user_id: ActingUser,
    service: Grader,
) -> BattleSpeechOutcome:
    """Grade a battle speech against the ruler's traits; a provider failure yields a 0% swing."""
    return await service.grade_speech(playthrough_id, acting_user_id, request)
