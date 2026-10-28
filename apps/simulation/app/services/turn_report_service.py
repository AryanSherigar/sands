from uuid import UUID

from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.models.api_turn import TurnReport
from app.models.world_events import EventLogEntry
from app.repositories import battle_exchange_repo, event_log_repo, world_state_repo
from app.services.campaign_state import player_faction
from app.services.campaign_transaction import require_owner
from app.services.turn_report_builder import build_turn_report
from psycopg import AsyncConnection


class TurnReportService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def get_report(
        self, playthrough_id: UUID, user_id: UUID, turn: int
    ) -> TurnReport:
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            events = await self._load_turn_events(playthrough_id, turn)
            receipts = await battle_exchange_repo.list_exchanges_for_turn(
                self._connection, playthrough_id, turn
            )
            return build_turn_report(
                turn, events, receipts, world, player_faction(world)
            )

    async def _load_turn_events(
        self, playthrough_id: UUID, turn: int
    ) -> list[EventLogEntry]:
        events: list[EventLogEntry] = []
        while True:
            page = await event_log_repo.list_events(
                self._connection,
                playthrough_id,
                after_seq=events[-1].seq if events else 0,
                turn=turn,
            )
            events.extend(page)
            if len(page) < event_log_repo.EVENT_PAGE_LIMIT:
                return events
