from uuid import UUID

from app.models.art_delivery import ArtDelivery
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.art import ArtBriefing

ENSURE = """INSERT INTO art_deliveries(playthrough_id, kind, item_id) VALUES (%s,%s,%s)
ON CONFLICT DO NOTHING"""
SAVE_BRIEFING = """UPDATE art_deliveries SET briefing=%s
WHERE playthrough_id=%s AND kind=%s AND item_id=%s AND briefing IS NULL"""
SELECT = (
    "SELECT * FROM art_deliveries WHERE playthrough_id=%s AND kind=%s AND item_id=%s"
)
CLAIM = """UPDATE art_deliveries SET status='generating', attempts=attempts+1,
claim_id=%s, lease_token=%s, lease_expires_at=now()+make_interval(secs => %s), error_code=NULL
WHERE playthrough_id=%s AND kind=%s AND item_id=%s AND status<>'completed' AND attempts<%s
AND (status<>'generating' OR lease_expires_at<=now()) RETURNING *"""
COMPLETE = """UPDATE art_deliveries SET status='completed', art_url=%s,
completed_at=now(), error_code=NULL WHERE playthrough_id=%s AND kind=%s AND item_id=%s
AND status='generating' AND lease_token=%s AND lease_expires_at>now() RETURNING item_id"""
FAIL = """UPDATE art_deliveries SET status='failed', error_code=%s
WHERE playthrough_id=%s AND kind=%s AND item_id=%s AND status='generating'
AND lease_token=%s AND lease_expires_at>now() RETURNING item_id"""


async def ensure_row(
    connection: AsyncConnection, identity: UUID, kind: str, item_id: str
) -> None:
    await connection.execute(ENSURE, (identity, kind, item_id))


async def save_briefing(
    connection: AsyncConnection,
    identity: UUID,
    kind: str,
    item_id: str,
    briefing: ArtBriefing,
) -> None:
    await connection.execute(
        SAVE_BRIEFING,
        (Jsonb(briefing.model_dump(mode="json")), identity, kind, item_id),
    )


async def get(
    connection: AsyncConnection,
    identity: UUID,
    kind: str,
    item_id: str,
    should_lock: bool = False,
) -> ArtDelivery | None:
    query = SELECT + (" FOR UPDATE" if should_lock else "")
    async with connection.cursor(row_factory=class_row(ArtDelivery)) as cursor:
        await cursor.execute(query, (identity, kind, item_id))
        return await cursor.fetchone()


async def claim(
    connection: AsyncConnection,
    identity: UUID,
    kind: str,
    item_id: str,
    claim_id: UUID,
    token: UUID,
    seconds: int,
    attempts: int,
) -> ArtDelivery | None:
    async with connection.cursor(row_factory=class_row(ArtDelivery)) as cursor:
        await cursor.execute(
            CLAIM, (claim_id, token, seconds, identity, kind, item_id, attempts)
        )
        return await cursor.fetchone()


async def complete(
    connection: AsyncConnection,
    identity: UUID,
    kind: str,
    item_id: str,
    token: UUID,
    art_url: str,
) -> bool:
    cursor = await connection.execute(
        COMPLETE, (art_url, identity, kind, item_id, token)
    )
    return await cursor.fetchone() is not None


async def fail(
    connection: AsyncConnection,
    identity: UUID,
    kind: str,
    item_id: str,
    token: UUID,
    code: str,
) -> bool:
    cursor = await connection.execute(FAIL, (code, identity, kind, item_id, token))
    return await cursor.fetchone() is not None
