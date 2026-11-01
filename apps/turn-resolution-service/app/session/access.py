"""Access validation for session (spectate/notifications) SSE endpoints.

Owns repository instantiation for the session routers, mirroring how
turn/pipeline.py owns repository instantiation for the turn router — routers
themselves never touch a repo directly (CLAUDE.md).
"""

import uuid
from datetime import UTC, datetime

from app.exceptions.session_exceptions import InvalidShareTokenError
from app.exceptions.turn_exceptions import ParticipantNotFoundError
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.share_repo import ShareRepo
from sqlalchemy.ext.asyncio import AsyncSession


async def validate_spectate_access(
    playthrough_id: uuid.UUID, share_token: str, session: AsyncSession
) -> None:
    """Raise InvalidShareTokenError unless the token is a valid, unexpired,
    unrevoked spectate token here."""
    share = await ShareRepo(session).get_by_token(share_token)
    if (
        share is None
        or share.mode != "spectate"
        or share.playthrough_id != playthrough_id
        or share.revoked_at is not None
        or share.expires_at <= datetime.now(UTC)
    ):
        raise InvalidShareTokenError()


async def validate_notification_access(
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    """Raise ParticipantNotFoundError unless participant_id belongs to this user here."""
    participant = await ParticipantRepo(session).get_by_id(participant_id)
    if (
        participant is None
        or participant.playthrough_id != playthrough_id
        or participant.user_id != user_id
    ):
        raise ParticipantNotFoundError()
