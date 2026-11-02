from uuid import UUID

from app.models.epilogue_delivery import EpilogueDelivery
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.epilogue import EpilogueBriefing

INSERT = """INSERT INTO epilogue_deliveries(playthrough_id, briefing, input_hash)
VALUES (%s,%s,%s) ON CONFLICT (playthrough_id) DO NOTHING"""
SELECT = "SELECT * FROM epilogue_deliveries WHERE playthrough_id=%s"
CLAIM = """UPDATE epilogue_deliveries SET status='generating', attempts=attempts+1,
claim_id=%s, lease_token=%s, lease_expires_at=now()+make_interval(secs => %s), error_code=NULL
WHERE playthrough_id=%s AND status<>'completed' AND attempts<%s
AND (status<>'generating' OR lease_expires_at<=now()) RETURNING *"""
COMPLETE = """UPDATE epilogue_deliveries SET status='completed', narration=%s, completion_hash=%s,
completed_at=now(), error_code=NULL WHERE playthrough_id=%s
AND status='generating' AND lease_token=%s AND lease_expires_at>now() RETURNING playthrough_id"""
FAIL = """UPDATE epilogue_deliveries SET status='failed', error_code=%s
WHERE playthrough_id=%s AND status='generating' AND lease_token=%s
AND lease_expires_at>now() RETURNING playthrough_id"""


async def insert_if_absent(
    connection: AsyncConnection, briefing: EpilogueBriefing, digest: str
) -> None:
    await connection.execute(
        INSERT,
        (briefing.playthrough_id, Jsonb(briefing.model_dump(mode="json")), digest),
    )


async def get(
    connection: AsyncConnection, identity: UUID, should_lock: bool = False
) -> EpilogueDelivery | None:
    query = SELECT + (" FOR UPDATE" if should_lock else "")
    async with connection.cursor(row_factory=class_row(EpilogueDelivery)) as cursor:
        await cursor.execute(query, (identity,))
        return await cursor.fetchone()


async def claim(
    connection: AsyncConnection,
    identity: UUID,
    claim_id: UUID,
    token: UUID,
    seconds: int,
    attempts: int,
) -> EpilogueDelivery | None:
    async with connection.cursor(row_factory=class_row(EpilogueDelivery)) as cursor:
        await cursor.execute(CLAIM, (claim_id, token, seconds, identity, attempts))
        return await cursor.fetchone()


async def complete(
    connection: AsyncConnection,
    identity: UUID,
    token: UUID,
    narration: str,
    digest: str,
) -> bool:
    cursor = await connection.execute(COMPLETE, (narration, digest, identity, token))
    return await cursor.fetchone() is not None


async def fail(
    connection: AsyncConnection, identity: UUID, token: UUID, code: str
) -> bool:
    cursor = await connection.execute(FAIL, (code, identity, token))
    return await cursor.fetchone() is not None
