from uuid import UUID

from app.models.battle_intelligence import BattleIntent
from app.models.battle_progress import IntentRequest
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

MAX_CLAIM_COUNT = 2
LEASE_SECONDS = 5
CLAIM_LOCK_KEY = 7311915403
INSERT_SQL = """INSERT INTO intent_requests
(playthrough_id, request_id, battle_id, faction_id, campaign_turn, intended_wave,
 input_hash, observation_fingerprint, policy_version, redacted_input, fallback)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT DO NOTHING RETURNING request_id"""
EXPIRE_SQL = """UPDATE intent_requests SET state = 'fallback', candidate = fallback,
lease_token = NULL, lease_expires_at = NULL
WHERE state = 'leased' AND lease_expires_at <= now()"""
LOCK_SQL = "SELECT pg_advisory_xact_lock(%s)"
CLAIM_SQL = """WITH eligible AS (
    SELECT playthrough_id, request_id FROM intent_requests WHERE state = 'pending'
    ORDER BY created_at, playthrough_id, request_id
    LIMIT GREATEST(0, LEAST(%s, %s - (SELECT count(*) FROM intent_requests WHERE state = 'leased')))
    FOR UPDATE SKIP LOCKED
)
UPDATE intent_requests AS request SET state = 'leased', attempts = 1,
lease_token = %s, lease_expires_at = now() + %s * interval '1 second'
FROM eligible WHERE request.playthrough_id = eligible.playthrough_id
AND request.request_id = eligible.request_id RETURNING request.*"""
COMPLETE_SQL = """UPDATE intent_requests SET candidate = %s, state = 'completed',
lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND request_id = %s AND state = 'leased'
AND lease_token = %s AND lease_expires_at > now()
AND input_hash = %s AND observation_fingerprint = %s AND policy_version = %s
AND battle_id = %s AND faction_id = %s AND campaign_turn = %s
AND intended_wave = %s RETURNING request_id"""
FAIL_SQL = """UPDATE intent_requests SET candidate = fallback, state = 'fallback',
lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND request_id = %s AND state = 'leased'
AND lease_token = %s RETURNING request_id"""
FREEZE_SQL = """UPDATE intent_requests SET state = 'activated',
candidate = COALESCE(candidate, fallback), lease_token = NULL, lease_expires_at = NULL
WHERE playthrough_id = %s AND campaign_turn = %s AND intended_wave <= %s
AND state <> 'activated' RETURNING candidate"""


async def insert_request(connection: AsyncConnection, request: IntentRequest) -> bool:
    cursor = await connection.execute(
        INSERT_SQL,
        (
            request.playthrough_id,
            request.request_id,
            request.battle_id,
            request.faction_id,
            request.campaign_turn,
            request.intended_wave,
            request.input_hash,
            request.observation_fingerprint,
            request.policy_version,
            Jsonb(request.redacted_input.model_dump(mode="json")),
            Jsonb(request.fallback.model_dump(mode="json")),
        ),
    )
    return await cursor.fetchone() is not None


async def claim_requests(
    connection: AsyncConnection, lease_token: UUID, limit: int = MAX_CLAIM_COUNT
) -> list[IntentRequest]:
    """Caller owns a short transaction; the advisory lock enforces the global in-flight cap."""
    await connection.execute(LOCK_SQL, (CLAIM_LOCK_KEY,))
    await connection.execute(EXPIRE_SQL)
    async with connection.cursor(row_factory=class_row(IntentRequest)) as cursor:
        await cursor.execute(
            CLAIM_SQL,
            (
                min(max(limit, 0), MAX_CLAIM_COUNT),
                MAX_CLAIM_COUNT,
                lease_token,
                LEASE_SECONDS,
            ),
        )
        return await cursor.fetchall()


async def complete_request(
    connection: AsyncConnection,
    playthrough_id: UUID,
    request_id: str,
    lease_token: UUID,
    candidate: BattleIntent,
) -> bool:
    cursor = await connection.execute(
        COMPLETE_SQL,
        (
            Jsonb(candidate.model_dump(mode="json")),
            playthrough_id,
            request_id,
            lease_token,
            candidate.input_hash,
            candidate.observation_fingerprint,
            candidate.policy_version,
            candidate.battle_id,
            candidate.faction_id,
            candidate.campaign_turn,
            candidate.intended_wave,
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


async def freeze_intents(
    connection: AsyncConnection, playthrough_id: UUID, campaign_turn: int, wave: int
) -> dict[str, BattleIntent]:
    cursor = await connection.execute(FREEZE_SQL, (playthrough_id, campaign_turn, wave))
    candidates = [
        BattleIntent.model_validate(row[0]) for row in await cursor.fetchall()
    ]
    return {candidate.id: candidate for candidate in candidates}
