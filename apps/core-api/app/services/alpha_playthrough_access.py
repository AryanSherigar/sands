import uuid

from app.exceptions.playthrough_exceptions import PlaythroughNotFoundError
from app.repositories.participant_repo import ParticipantRepo


async def require_playthrough_participant(
    participant_repo: ParticipantRepo, playthrough_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Raises 404 (not 403) so another tester's playthrough id is not confirmed."""
    participant = await participant_repo.get_by_playthrough_and_user(
        playthrough_id, user_id
    )
    if participant is None:
        raise PlaythroughNotFoundError()
