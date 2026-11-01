"""Records a truncated player action as a server-source alpha event.

Uses its own short session, like the quota event recorder, and never raises:
a turn must not depend on telemetry.
"""

import uuid

import structlog
from app.config import settings
from app.db.connection import AsyncSessionFactory
from app.models.turn import InputTruncation
from app.repositories.alpha_event_repo import AlphaEventRepo
from app.repositories.user_repo import UserRepo
from app.services.rate_limit.store import STORE_ERRORS, SessionFactory

logger = structlog.get_logger()

EVENT_INPUT_TRUNCATED_NAME = "input_truncated"
EVENT_INPUT_TRUNCATED_RECORD_FAILED = "input_truncated_record_failed"


class InputLimitEventRecorder:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def record_truncated(
        self, user_id: uuid.UUID, truncation: InputTruncation
    ) -> None:
        if not settings.is_alpha_mode:
            return
        try:
            await self._write(user_id, truncation)
        except STORE_ERRORS as error:
            logger.warning(EVENT_INPUT_TRUNCATED_RECORD_FAILED, error=str(error))

    async def _write(self, user_id: uuid.UUID, truncation: InputTruncation) -> None:
        async with self._session_factory() as session:
            consent = await UserRepo(session).get_alpha_consent_version(user_id)
            if consent != settings.alpha_consent_version:
                return
            await AlphaEventRepo(session).add_server_event(
                user_id,
                settings.alpha_server_event_session_id,
                EVENT_INPUT_TRUNCATED_NAME,
                truncation.model_dump(),
            )
            await session.commit()


def get_input_limit_event_recorder() -> InputLimitEventRecorder:
    return InputLimitEventRecorder(AsyncSessionFactory)
