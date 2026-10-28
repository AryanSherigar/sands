from uuid import UUID

from app.models.stance import StanceChoice, StanceRequest
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.ids import LeaderId

MAX_CLAIM_COUNT = 4
LEASE_SECONDS = 15
CLAIM_LOCK_KEY = 7311915404
INSERT_SQL = """INSERT INTO stance_requests
(playthrough_id, request_id, leader_id, faction_id, due_turn, input_hash,
 briefing, fallback, candidate, state)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT DO NOTHING RETURNING request_id"""
EXPIRE_SQL = """UPDATE stance_requests SET state = 'fallback', candidate = fallback,
lease_token = NULL, lease_expires_at = NULL
WHERE state = 'leased' AND lease_expires_at <= now()"""
LOCK_SQL = "SELECT pg_advisory_xact_lock(%s)"
CLAIM_SQL = """WITH eligible AS (
    SELECT playthrough_id, request_id FROM stance_requests WHERE state = 'pending'
    ORDER BY created_at, playthrough_id, request_id
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
UPDATE stance_requests AS request SET state = 'leased', attempts = 1,
lease_token = %s, lease_expires_at = now() + %s * interval '1 second'
FROM eligible WHERE request.playthrough_id = eligible.playthrough_id
AND request.request_id = eligible.request_id RETURNING request.*"""
COMPLETE_SQL = """UPDATE stance_requests SET candidate = %s, state = 'completed',
lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND request_id = %s AND state = 'leased'
AND lease_token = %s AND lease_expires_at > now()
AND input_hash = %s AND leader_id = %s AND due_turn = %s RETURNING request_id"""
FAIL_SQL = """UPDATE stance_requests SET candidate = fallback, state = 'fallback',
lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND request_id = %s AND state = 'leased'
AND lease_token = %s RETURNING request_id"""
FREEZE_SQL = """SELECT COALESCE(candidate, fallback) FROM stance_requests
WHERE playthrough_id = %s AND due_turn = %s ORDER BY leader_id FOR UPDATE"""
ACTIVATE_SQL = """UPDATE stance_requests SET state = 'activated',
candidate = COALESCE(candidate, fallback), lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND due_turn <= %s AND state <> 'activated'"""


async def insert_request(
    connection: AsyncConnection,
    request: StanceRequest,
    is_fallback_only: bool = False,
) -> bool:
    candidate = request.fallback if is_fallback_only else None
    cursor = await connection.execute(
        INSERT_SQL,
        (
            request.playthrough_id,
            request.request_id,
            request.leader_id,
            request.faction_id,
            request.due_turn,
            request.input_hash,
            Jsonb(request.briefing.model_dump(mode="json")),
            Jsonb(request.fallback.model_dump(mode="json")),
            Jsonb(candidate.model_dump(mode="json")) if candidate else None,
            "fallback" if is_fallback_only else "pending",
        ),
    )
    return await cursor.fetchone() is not None


async def claim_requests(
    connection: AsyncConnection, lease_token: UUID, limit: int = MAX_CLAIM_COUNT
) -> list[StanceRequest]:
    """Caller owns a short transaction; the advisory lock serialises claim and expiry."""
    await connection.execute(LOCK_SQL, (CLAIM_LOCK_KEY,))
    await connection.execute(EXPIRE_SQL)
    async with connection.cursor(row_factory=class_row(StanceRequest)) as cursor:
        await cursor.execute(
            CLAIM_SQL, (min(max(limit, 0), MAX_CLAIM_COUNT), lease_token, LEASE_SECONDS)
        )
        return await cursor.fetchall()


async def complete_request(
    connection: AsyncConnection,
    playthrough_id: UUID,
    request_id: str,
    lease_token: UUID,
    candidate: StanceChoice,
) -> bool:
    cursor = await connection.execute(
        COMPLETE_SQL,
        (
            Jsonb(candidate.model_dump(mode="json")),
            playthrough_id,
            request_id,
            lease_token,
            candidate.input_hash,
            candidate.leader_id,
            candidate.due_turn,
        ),
    )
    return await cursor.fetchone() is not None


async def fail_request(
    connection: AsyncConnection,
    playthrough_id: UUID,
    request_id: str,
    lease_token: UUID,
) -> bool:
    cursor = await connection.execute(
        FAIL_SQL, (playthrough_id, request_id, lease_token)
    )
    return await cursor.fetchone() is not None


async def freeze_stances(
    connection: AsyncConnection, playthrough_id: UUID, due_turn: int
) -> dict[LeaderId, StanceChoice]:
    """Read the answers for one due turn and lock their rows until the caller's transaction ends."""
    cursor = await connection.execute(FREEZE_SQL, (playthrough_id, due_turn))
    choices = [StanceChoice.model_validate(row[0]) for row in await cursor.fetchall()]
    return {choice.leader_id: choice for choice in choices}


async def activate_stances(
    connection: AsyncConnection, playthrough_id: UUID, due_turn: int
) -> None:
    """Seal requests whose due turn has begun so a late model answer is dropped."""
    await connection.execute(ACTIVATE_SQL, (playthrough_id, due_turn))
