"""Playthrough sharing domain service: token issuance and validation."""

import secrets
import uuid
from datetime import UTC, datetime

import structlog
from app.config import settings
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import PRIVATE_VISIBILITY
from app.db.models.share import PlaythroughShare
from app.exceptions.playthrough_exceptions import (
    InvalidShareTokenError,
    PlaythroughAccessDeniedError,
    PlaythroughNotFoundError,
    ShareNotFoundError,
)
from app.exceptions.scenario_exceptions import PrivateScenarioShareError
from app.logging_config import log_audit_event
from app.models.share import ShareMode
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.share_repo import ShareRepo

logger = structlog.get_logger()

_TOKEN_BYTES = 32

EVENT_SHARE_LINK_CREATED = "share_link_created"


class ShareService:
    """Service orchestrating share token creation and validation."""

    def __init__(
        self,
        share_repo: ShareRepo,
        playthrough_repo: PlaythroughRepo,
        participant_repo: ParticipantRepo,
    ) -> None:
        self.share_repo = share_repo
        self.playthrough_repo = playthrough_repo
        self.participant_repo = participant_repo

    async def create_share(
        self, playthrough_id: uuid.UUID, mode: ShareMode, user_id: uuid.UUID
    ) -> PlaythroughShare:
        """Generate (or fetch an existing, still-valid) share link. Participant-only."""
        playthrough = await self._require_participant(playthrough_id, user_id)
        if playthrough.scenario_snapshot.get("visibility") == PRIVATE_VISIBILITY:
            raise PrivateScenarioShareError()
        existing = await self.share_repo.get_by_playthrough_and_mode(
            playthrough_id, mode
        )
        if existing and _is_share_valid(existing):
            return existing
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        created = await self.share_repo.issue(
            playthrough_id=playthrough_id, mode=mode, share_token=token
        )
        log_audit_event(
            logger,
            EVENT_SHARE_LINK_CREATED,
            playthrough_id=str(playthrough_id),
            share_type=mode,
        )
        return created

    async def validate_token(
        self, share_token: str, required_mode: ShareMode | None = None
    ) -> PlaythroughShare:
        """Look up a token, raising InvalidShareTokenError if invalid, expired,
        revoked, or for the wrong mode."""
        share = await self.share_repo.get_by_token(share_token)
        if (
            share is None
            or (required_mode and share.mode != required_mode)
            or not _is_share_valid(share)
        ):
            raise InvalidShareTokenError()
        return share

    async def revoke_share(
        self, playthrough_id: uuid.UUID, share_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Revoke a share link. Owner-only."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if playthrough is None:
            raise PlaythroughNotFoundError()
        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if participant is None or participant.role != "owner":
            raise PlaythroughAccessDeniedError()

        share = await self.share_repo.get_by_id(share_id)
        if share is None or share.playthrough_id != playthrough_id:
            raise ShareNotFoundError()
        await self.share_repo.revoke(share)

    async def _require_participant(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> Playthrough:
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if playthrough is None:
            raise PlaythroughNotFoundError()
        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if participant is None:
            raise PlaythroughAccessDeniedError()
        return playthrough


def _is_share_valid(share: PlaythroughShare) -> bool:
    return share.revoked_at is None and share.expires_at > datetime.now(UTC)


def build_share_url(share: PlaythroughShare) -> str:
    """Build the frontend-facing shareable URL for a share token."""
    if share.mode == "spectate":
        return (
            f"{settings.frontend_base_url}/spectate/{share.playthrough_id}"
            f"?token={share.share_token}"
        )
    return f"{settings.frontend_base_url}/join?token={share.share_token}"
