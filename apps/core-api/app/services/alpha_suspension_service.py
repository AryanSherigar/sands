import uuid
from datetime import datetime, timezone

import structlog
from app.db.models.user import User
from app.exceptions.user_exceptions import UserNotFoundError
from app.logging_config import log_audit_event
from app.repositories.user_repo import UserRepo

logger = structlog.get_logger()

EVENT_ALPHA_USER_SUSPENDED = "alpha_user_suspended"
EVENT_ALPHA_USER_RESTORED = "alpha_user_restored"


class AlphaSuspensionService:
    def __init__(self, user_repo: UserRepo) -> None:
        self.user_repo = user_repo

    async def suspend(self, user_id: uuid.UUID) -> User:
        user = await self._get_user(user_id)
        if user.alpha_suspended_at is not None:
            return user
        await self.user_repo.mark_suspended(user, datetime.now(timezone.utc))
        log_audit_event(logger, EVENT_ALPHA_USER_SUSPENDED, user_id=str(user_id))
        return user

    async def restore(self, user_id: uuid.UUID) -> User:
        user = await self._get_user(user_id)
        if user.alpha_suspended_at is None:
            return user
        await self.user_repo.clear_suspension(user)
        log_audit_event(logger, EVENT_ALPHA_USER_RESTORED, user_id=str(user_id))
        return user

    async def _get_user(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user
