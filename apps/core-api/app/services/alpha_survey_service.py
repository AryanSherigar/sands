"""Stores a tester's intake and post-run survey answers."""

from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaSurveyAlreadySubmittedError
from app.models.alpha_survey import (
    AlphaSurveyAccepted,
    IntakeSurveyRequest,
    PostRunSurveyRequest,
)
from app.repositories.alpha_survey_repo import AlphaSurveyRepo
from app.repositories.participant_repo import ParticipantRepo
from app.services.alpha_consent import require_alpha_collection_consent
from app.services.alpha_playthrough_access import require_playthrough_participant


class AlphaSurveyService:
    def __init__(
        self, survey_repo: AlphaSurveyRepo, participant_repo: ParticipantRepo
    ) -> None:
        self._survey_repo = survey_repo
        self._participant_repo = participant_repo

    async def submit(
        self, user: User, request: IntakeSurveyRequest | PostRunSurveyRequest
    ) -> AlphaSurveyAccepted:
        require_alpha_collection_consent(user)
        playthrough_id = None
        if isinstance(request, PostRunSurveyRequest):
            playthrough_id = request.playthrough_id
            await require_playthrough_participant(
                self._participant_repo, playthrough_id, user.user_id
            )
        is_new = await self._survey_repo.create_if_absent(
            user.user_id, playthrough_id, request.kind, request.answers.model_dump()
        )
        if not is_new:
            raise AlphaSurveyAlreadySubmittedError()
        return AlphaSurveyAccepted(kind=request.kind)
