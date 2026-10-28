from uuid import UUID

from app.models.battle_progress import MutationResponse, OperationRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

GET_SQL = """SELECT * FROM simulation_operations
WHERE playthrough_id = %s AND actor_id = %s AND operation_id = %s"""
INSERT_SQL = """INSERT INTO simulation_operations
(playthrough_id, actor_id, operation_id, request_hash, route_kind, status_code,
 result_version, response, committed_sequence)
VALUES (%s, %s, %s, %s, %s, 200, %s, %s, %s)"""
INITIALIZATION_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"


async def lock_initialization(
    connection: AsyncConnection, playthrough_id: UUID
) -> None:
    await connection.execute(INITIALIZATION_LOCK_SQL, (str(playthrough_id),))


async def get_operation(
    connection: AsyncConnection, playthrough_id: UUID, actor_id: str, operation_id: str
) -> OperationRow | None:
    async with connection.cursor(row_factory=class_row(OperationRow)) as cursor:
        await cursor.execute(GET_SQL, (playthrough_id, actor_id, operation_id))
        return await cursor.fetchone()


async def insert_operation(
    connection: AsyncConnection,
    playthrough_id: UUID,
    actor_id: str,
    request_hash: str,
    route_kind: str,
    response: MutationResponse,
    committed_sequence: int,
) -> None:
    await connection.execute(
        INSERT_SQL,
        (
            playthrough_id,
            actor_id,
            response.operation_id,
            request_hash,
            route_kind,
            response.world_version,
            Jsonb(response.model_dump(mode="json")),
            committed_sequence,
        ),
    )


async def get_initialization(
    connection: AsyncConnection, playthrough_id: UUID, actor_id: str
) -> OperationRow | None:
    query = """SELECT * FROM simulation_operations WHERE playthrough_id = %s
    AND actor_id = %s AND route_kind = 'initialize' ORDER BY created_at, operation_id LIMIT 1"""
    async with connection.cursor(row_factory=class_row(OperationRow)) as cursor:
        await cursor.execute(query, (playthrough_id, actor_id))
        return await cursor.fetchone()
