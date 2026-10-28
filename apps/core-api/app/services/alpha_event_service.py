"""Validates and stores a tester's client events."""

import uuid

import structlog
from app.db.models.alpha_event import EVENT_SOURCE_CLIENT, AlphaEvent
from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaConsentRequiredError
from app.models.alpha_event import AlphaEventIn, AlphaEventsRequest
from app.repositories.alpha_event_repo import AlphaEventRepo
from app.services.alpha_consent import require_alpha_collection_consent

logger = structlog.get_logger()

EVENT_ALPHA_EVENT_REJECTED = "alpha_event_rejected"
EVENT_ALPHA_EVENT_PLAYTHROUGH_DROPPED = "alpha_event_playthrough_dropped"
REASON_NO_CONSENT = "no_consent"


class AlphaEventService:
    def __init__(self, repo: AlphaEventRepo) -> None:
        self._repo = repo

    async def ingest(self, user: User, request: AlphaEventsRequest) -> int:
        """Store the batch; returns how many events were kept."""
        try:
            require_alpha_collection_consent(user)
        except AlphaConsentRequiredError:
            logger.info(EVENT_ALPHA_EVENT_REJECTED, reason=REASON_NO_CONSENT)
            raise
        allowed = await self._allowed_playthroughs(user, request.events)
        rows = [
            self._to_row(user, request.session_id, e, allowed) for e in request.events
        ]
        await self._repo.add_many(rows)
        return len(rows)

    async def _allowed_playthroughs(
        self, user: User, events: list[AlphaEventIn]
    ) -> set[uuid.UUID]:
        asked = {e.playthrough_id for e in events if e.playthrough_id is not None}
        allowed = await self._repo.list_playthroughs_of_user(user.user_id, asked)
        if asked - allowed:
            logger.info(
                EVENT_ALPHA_EVENT_PLAYTHROUGH_DROPPED,
                dropped_count=len(asked - allowed),
            )
        return allowed

    @staticmethod
    def _to_row(
        user: User,
        session_id: str,
        event: AlphaEventIn,
        allowed: set[uuid.UUID],
    ) -> AlphaEvent:
        is_allowed = event.playthrough_id in allowed
        return AlphaEvent(
            user_id=user.user_id,
            playthrough_id=event.playthrough_id if is_allowed else None,
            session_id=session_id,
            name=event.name.value,
            props=event.props,
            source=EVENT_SOURCE_CLIENT,
            client_ts=event.client_ts,
        )
