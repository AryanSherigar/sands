"""Stores a tester's free-text feedback and narration flags."""

import uuid

from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaTurnNotFoundError
from app.models.alpha_feedback import (
    AlphaFeedbackRequest,
    AlphaFeedbackResponse,
    AlphaFlagRequest,
    AlphaFlagResponse,
)
from app.repositories.alpha_feedback_repo import AlphaFeedbackRepo
from app.repositories.alpha_narration_flag_repo import AlphaNarrationFlagRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.services.alpha_consent import require_alpha_collection_consent
from app.services.alpha_playthrough_access import require_playthrough_participant


class AlphaFeedbackService:
    def __init__(
        self,
        feedback_repo: AlphaFeedbackRepo,
        flag_repo: AlphaNarrationFlagRepo,
        turn_log_repo: TurnLogRepo,
        participant_repo: ParticipantRepo,
    ) -> None:
        self._feedback_repo = feedback_repo
        self._flag_repo = flag_repo
        self._turn_log_repo = turn_log_repo
        self._participant_repo = participant_repo

    async def submit_feedback(
        self, user: User, request: AlphaFeedbackRequest
    ) -> AlphaFeedbackResponse:
        require_alpha_collection_consent(user)
        await require_playthrough_participant(
            self._participant_repo, request.playthrough_id, user.user_id
        )
        feedback = await self._feedback_repo.create(
            user.user_id,
            request.playthrough_id,
            request.turn_number,
            request.category,
            request.body,
        )
        return AlphaFeedbackResponse(feedback_id=feedback.feedback_id)

    async def flag_turn(
        self, user: User, turn_id: uuid.UUID, request: AlphaFlagRequest
    ) -> AlphaFlagResponse:
        require_alpha_collection_consent(user)
        turn = await self._turn_log_repo.get_by_id(turn_id)
        if turn is None:
            raise AlphaTurnNotFoundError()
        await self._require_turn_participant(turn.playthrough_id, user.user_id)
        flag = await self._flag_repo.upsert(
            user.user_id,
            turn.playthrough_id,
            turn.turn_id,
            list(request.reasons),
            request.note,
        )
        return AlphaFlagResponse(
            flag_id=flag.flag_id, turn_id=flag.turn_id, reasons=flag.reasons
        )

    async def _require_turn_participant(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        participant = await self._participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if participant is None:
            raise AlphaTurnNotFoundError()
