from uuid import UUID

from app.models.summary_delivery import SummaryDelivery
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.summary import SummaryAvailability, SummaryBriefing

INSERT = """INSERT INTO summary_deliveries(summary_id, playthrough_id, engine_request_id, briefing, input_hash)
VALUES (%s,%s,%s,%s,%s) ON CONFLICT (playthrough_id, engine_request_id) DO NOTHING"""
SELECT = "SELECT * FROM summary_deliveries WHERE playthrough_id=%s AND summary_id=%s"
PAGE = """SELECT * FROM summary_deliveries WHERE playthrough_id=%(playthrough_id)s
AND (%(after_id)s::uuid IS NULL OR (created_at,summary_id) > (
 SELECT created_at,summary_id FROM summary_deliveries WHERE summary_id=%(after_id)s AND playthrough_id=%(playthrough_id)s))
ORDER BY created_at,summary_id LIMIT %(limit)s"""
CLAIM = """UPDATE summary_deliveries SET status='generating', attempts=attempts+1,
claim_id=%s, lease_token=%s, lease_expires_at=now()+make_interval(secs => %s), error_code=NULL
WHERE playthrough_id=%s AND summary_id=%s AND status<>'completed' AND attempts<%s
AND (status<>'generating' OR lease_expires_at<=now()) RETURNING *"""
COMPLETE = """UPDATE summary_deliveries SET status='completed', narration=%s,completion_hash=%s,
completed_at=now(),error_code=NULL WHERE playthrough_id=%s AND summary_id=%s
AND status='generating' AND lease_token=%s AND lease_expires_at>now() RETURNING summary_id"""
FAIL = """UPDATE summary_deliveries SET status='failed',error_code=%s
WHERE playthrough_id=%s AND summary_id=%s AND status='generating' AND lease_token=%s
AND lease_expires_at>now() RETURNING summary_id"""


async def insert(
    connection: AsyncConnection, package: SummaryBriefing, engine_id: str, digest: str
) -> None:
    await connection.execute(
        INSERT,
        (
            package.summary_id,
            package.playthrough_id,
            engine_id,
            Jsonb(package.model_dump(mode="json")),
            digest,
        ),
    )


async def get(
    connection: AsyncConnection,
    identity: UUID,
    summary_id: UUID,
    should_lock: bool = False,
) -> SummaryDelivery | None:
    async with connection.cursor(row_factory=class_row(SummaryDelivery)) as cursor:
        await cursor.execute(
            SELECT + (" FOR UPDATE" if should_lock else ""), (identity, summary_id)
        )
        return await cursor.fetchone()


async def page(
    connection: AsyncConnection, identity: UUID, after: UUID | None, limit: int
) -> list[SummaryDelivery]:
    async with connection.cursor(row_factory=class_row(SummaryDelivery)) as cursor:
        await cursor.execute(
            PAGE, {"playthrough_id": identity, "after_id": after, "limit": limit}
        )
        return await cursor.fetchall()


async def claim(
    connection: AsyncConnection,
    identity: UUID,
    summary_id: UUID,
    claim_id: UUID,
    token: UUID,
    seconds: int,
    attempts: int,
) -> SummaryDelivery | None:
    async with connection.cursor(row_factory=class_row(SummaryDelivery)) as cursor:
        await cursor.execute(
            CLAIM, (claim_id, token, seconds, identity, summary_id, attempts)
        )
        return await cursor.fetchone()


async def complete(
    connection: AsyncConnection,
    identity: UUID,
    summary_id: UUID,
    token: UUID,
    narration: str,
    digest: str,
) -> bool:
    cursor = await connection.execute(
        COMPLETE, (narration, digest, identity, summary_id, token)
    )
    return await cursor.fetchone() is not None


async def fail(
    connection: AsyncConnection,
    identity: UUID,
    summary_id: UUID,
    token: UUID,
    code: str,
) -> bool:
    cursor = await connection.execute(FAIL, (code, identity, summary_id, token))
    return await cursor.fetchone() is not None


async def availability(
    connection: AsyncConnection, identity: UUID
) -> SummaryAvailability:

    cursor = await connection.execute(
        """SELECT
        count(*) FILTER (WHERE status <> 'completed'),
        (SELECT summary_id FROM summary_deliveries WHERE playthrough_id=%s
         ORDER BY created_at DESC,summary_id DESC LIMIT 1)
        FROM summary_deliveries WHERE playthrough_id=%s""",
        (identity, identity),
    )
    row = await cursor.fetchone()
    return SummaryAvailability(pending_count=row[0], latest_summary_id=row[1])
