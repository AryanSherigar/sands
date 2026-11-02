from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models.event_delivery import EventDelivery
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.events import (
    EventNarrativeBriefing,
    EventNarrativeClaim,
    EventNarrativePayload,
)

LEASE_SECONDS = 60

SQL_INSERT_PENDING = """
INSERT INTO event_deliveries (playthrough_id, event_id, turn, briefing, status, created_at)
VALUES (%s, %s, %s, %s, 'pending', NOW())
ON CONFLICT (playthrough_id, event_id) DO NOTHING
"""

SQL_GET = """
SELECT playthrough_id, event_id, turn, briefing, status, attempts,
       claim_id, lease_token, lease_expires_at, narration, error_code,
       created_at, completed_at
FROM event_deliveries
WHERE playthrough_id = %s AND event_id = %s
"""

SQL_CLAIM = """
UPDATE event_deliveries
SET status = 'generating',
    attempts = attempts + 1,
    claim_id = %s,
    lease_token = %s,
    lease_expires_at = %s,
    error_code = NULL
WHERE playthrough_id = %s
  AND event_id = %s
  AND (status = 'pending' OR (status = 'generating' AND lease_expires_at < NOW()) OR status = 'failed')
RETURNING playthrough_id, event_id, turn, briefing, status, attempts,
          claim_id, lease_token, lease_expires_at, narration, error_code,
          created_at, completed_at
"""

SQL_COMPLETE = """
UPDATE event_deliveries
SET status = 'completed',
    narration = %s,
    completed_at = NOW(),
    lease_token = NULL,
    lease_expires_at = NULL,
    error_code = NULL
WHERE playthrough_id = %s AND event_id = %s AND lease_token = %s
"""

SQL_FAIL = """
UPDATE event_deliveries
SET status = 'failed',
    error_code = %s,
    lease_token = NULL,
    lease_expires_at = NULL
WHERE playthrough_id = %s AND event_id = %s AND lease_token = %s
"""


class EventDeliveryRepo:
    async def insert_pending(
        self,
        connection: AsyncConnection,
        playthrough_id: UUID,
        event_id: str,
        turn: int,
        briefing: EventNarrativeBriefing,
    ) -> None:
        await connection.execute(
            SQL_INSERT_PENDING,
            (
                playthrough_id,
                event_id,
                turn,
                Jsonb(briefing.model_dump(mode="json")),
            ),
        )

    async def get(
        self, connection: AsyncConnection, playthrough_id: UUID, event_id: str
    ) -> EventDelivery | None:
        async with connection.cursor(row_factory=class_row(EventDelivery)) as cursor:
            await cursor.execute(SQL_GET, (playthrough_id, event_id))
            return await cursor.fetchone()

    async def claim(
        self,
        connection: AsyncConnection,
        playthrough_id: UUID,
        event_id: str,
        claim_id: UUID,
    ) -> EventNarrativeClaim | None:
        token = uuid4()
        lease_expires_at = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)
        async with connection.cursor(row_factory=class_row(EventDelivery)) as cursor:
            await cursor.execute(
                SQL_CLAIM,
                (claim_id, token, lease_expires_at, playthrough_id, event_id),
            )
            row = await cursor.fetchone()
            if row is None or row.lease_token is None:
                return None
            return EventNarrativeClaim(
                lease_token=row.lease_token, briefing=row.briefing
            )

    async def complete(
        self,
        connection: AsyncConnection,
        playthrough_id: UUID,
        event_id: str,
        token: UUID,
        payload: EventNarrativePayload,
    ) -> bool:
        async with connection.cursor() as cursor:
            await cursor.execute(
                SQL_COMPLETE,
                (
                    Jsonb(payload.model_dump(mode="json")),
                    playthrough_id,
                    event_id,
                    token,
                ),
            )
            return cursor.rowcount > 0

    async def fail(
        self,
        connection: AsyncConnection,
        playthrough_id: UUID,
        event_id: str,
        token: UUID,
        error_code: str,
    ) -> None:
        await connection.execute(
            SQL_FAIL,
            (error_code, playthrough_id, event_id, token),
        )
