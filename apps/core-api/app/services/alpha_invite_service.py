import hashlib
import secrets
import uuid

import structlog
from app.db.models.alpha_invite import AlphaInvite
from app.exceptions.alpha_exceptions import (
    AlphaInviteInvalidError,
    AlphaInviteTargetRequiredError,
)
from app.logging_config import log_audit_event
from app.repositories.alpha_invite_repo import AlphaInviteRepo

logger = structlog.get_logger()

EVENT_ALPHA_SIGNUP_REFUSED = "alpha_signup_refused"
EVENT_ALPHA_INVITE_REDEEMED = "alpha_invite_redeemed"
EVENT_ALPHA_INVITE_REVOKED = "alpha_invite_revoked"

INVITE_CODE_BYTES = 32


class AlphaInviteService:
    def __init__(self, invite_repo: AlphaInviteRepo) -> None:
        self.invite_repo = invite_repo

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def redeem(self, code: str) -> uuid.UUID:
        code_hash = self.hash_code(code)
        invite_id = await self.invite_repo.redeem_seat(code_hash)
        if invite_id is None:
            reason = await self.invite_repo.get_refusal_reason(code_hash)
            logger.warning(EVENT_ALPHA_SIGNUP_REFUSED, reason=reason)
            raise AlphaInviteInvalidError()
        log_audit_event(logger, EVENT_ALPHA_INVITE_REDEEMED, invite_id=str(invite_id))
        return invite_id

    async def record_redemption(self, invite_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self.invite_repo.add_redemption(invite_id, user_id)

    async def create_invite(
        self, label: str, max_seats: int, expires_days: int | None
    ) -> str:
        code = secrets.token_urlsafe(INVITE_CODE_BYTES)
        await self.invite_repo.create_invite(
            self.hash_code(code), label, max_seats, expires_days
        )
        return code

    async def list_invites(self) -> list[AlphaInvite]:
        return await self.invite_repo.list_invites()

    async def revoke(self, label: str | None, invite_id: uuid.UUID | None) -> int:
        if invite_id is not None:
            revoked = await self.invite_repo.revoke_by_id(invite_id)
        elif label is not None:
            revoked = await self.invite_repo.revoke_by_label(label)
        else:
            raise AlphaInviteTargetRequiredError()
        log_audit_event(logger, EVENT_ALPHA_INVITE_REVOKED, revoked_count=revoked)
        return revoked
