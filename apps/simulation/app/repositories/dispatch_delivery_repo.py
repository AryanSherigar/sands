from uuid import UUID

from app.models.dispatch_delivery import DispatchDelivery
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.agents import DispatchBriefing

INSERT = """INSERT INTO dispatch_deliveries(playthrough_id, rumor_id, turn, briefing)
VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING"""
SELECT = "SELECT * FROM dispatch_deliveries WHERE playthrough_id=%s AND rumor_id=%s"
LIST_PAGE = """SELECT * FROM dispatch_deliveries WHERE playthrough_id=%s
ORDER BY turn DESC, rumor_id LIMIT %s"""
CLAIM = """UPDATE dispatch_deliveries SET status='generating', attempts=attempts+1,
claim_id=%s, lease_token=%s, lease_expires_at=now()+make_interval(secs => %s), error_code=NULL
WHERE playthrough_id=%s AND rumor_id=%s AND status<>'completed' AND attempts<%s
AND (status<>'generating' OR lease_expires_at<=now()) RETURNING *"""
COMPLETE = """UPDATE dispatch_deliveries SET status='completed', narration=%s,
completed_at=now(), error_code=NULL WHERE playthrough_id=%s AND rumor_id=%s
AND status='generating' AND lease_token=%s AND lease_expires_at>now() RETURNING rumor_id"""
FAIL = """UPDATE dispatch_deliveries SET status='failed', error_code=%s
WHERE playthrough_id=%s AND rumor_id=%s AND status='generating'
AND lease_token=%s AND lease_expires_at>now() RETURNING rumor_id"""


async def insert(connection: AsyncConnection, briefing: DispatchBriefing) -> None:
    await connection.execute(
        INSERT,
        (
            briefing.playthrough_id,
            briefing.rumor_id,
            briefing.turn,
            Jsonb(briefing.model_dump(mode="json")),
        ),
    )


async def get(
    connection: AsyncConnection,
    identity: UUID,
    rumor_id: str,
    should_lock: bool = False,
) -> DispatchDelivery | None:
    query = SELECT + (" FOR UPDATE" if should_lock else "")
    async with connection.cursor(row_factory=class_row(DispatchDelivery)) as cursor:
        await cursor.execute(query, (identity, rumor_id))
        return await cursor.fetchone()


async def list_page(
    connection: AsyncConnection, identity: UUID, limit: int
) -> list[DispatchDelivery]:
    async with connection.cursor(row_factory=class_row(DispatchDelivery)) as cursor:
        await cursor.execute(LIST_PAGE, (identity, limit))
        return await cursor.fetchall()


async def claim(
    connection: AsyncConnection,
    identity: UUID,
    rumor_id: str,
    claim_id: UUID,
    token: UUID,
    seconds: int,
    max_attempts: int,
) -> DispatchDelivery | None:
    async with connection.cursor(row_factory=class_row(DispatchDelivery)) as cursor:
        await cursor.execute(
            CLAIM, (claim_id, token, seconds, identity, rumor_id, max_attempts)
        )
        return await cursor.fetchone()


async def complete(
    connection: AsyncConnection,
    identity: UUID,
    rumor_id: str,
    token: UUID,
    narration: str,
) -> bool:
    cursor = await connection.execute(COMPLETE, (narration, identity, rumor_id, token))
    return await cursor.fetchone() is not None


async def fail(
    connection: AsyncConnection,
    identity: UUID,
    rumor_id: str,
    token: UUID,
    code: str,
) -> bool:
    cursor = await connection.execute(FAIL, (code, identity, rumor_id, token))
    return await cursor.fetchone() is not None
