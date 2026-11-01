"""Records a tripped quota as a server-source alpha event.

The quota counters expire with their window, so this row is the only durable
trace that a tester hit a limit. It uses its own short session, like the rate
limit store, and never raises: a quota decision must not depend on it.
"""

import uuid

import structlog
from app.config import settings
from app.repositories.alpha_event_repo import AlphaEventRepo
from app.repositories.user_repo import UserRepo
from app.services.rate_limit.store import STORE_ERRORS, SessionFactory

logger = structlog.get_logger()

EVENT_QUOTA_EXCEEDED_NAME = "quota_exceeded"
EVENT_QUOTA_EVENT_FAILED = "quota_event_failed"
SCOPE_USER = "user"
SCOPE_GLOBAL = "global"


class QuotaEventRecorder:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def record_exceeded(
        self, user_id: uuid.UUID, feature: str, *, is_global: bool
    ) -> None:
        if not settings.is_alpha_mode:
            return
        scope = SCOPE_GLOBAL if is_global else SCOPE_USER
        try:
            await self._write(user_id, {"feature": feature, "scope": scope})
        except STORE_ERRORS as error:
            logger.warning(EVENT_QUOTA_EVENT_FAILED, feature=feature, error=str(error))

    async def _write(self, user_id: uuid.UUID, props: dict[str, object]) -> None:
        async with self._session_factory() as session:
            consent = await UserRepo(session).get_alpha_consent_version(user_id)
            if consent != settings.alpha_consent_version:
                return
            await AlphaEventRepo(session).add_server_event(
                user_id,
                settings.alpha_server_event_session_id,
                EVENT_QUOTA_EXCEEDED_NAME,
                props,
            )
            await session.commit()
