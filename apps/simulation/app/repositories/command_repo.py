from collections.abc import Sequence
from uuid import UUID

from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import AcceptedCommand
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

UPSERT_SQL = """INSERT INTO simulation_commands
(playthrough_id, command_id, actor_id, operation_id, faction_id, battle_id,
 accepted_turn, accepted_wave, execution_turn, reserved_cost, status, failure_reason, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (playthrough_id, command_id) DO UPDATE SET
status = EXCLUDED.status, failure_reason = EXCLUDED.failure_reason, payload = EXCLUDED.payload"""
DELETE_SQL = (
    "DELETE FROM simulation_commands WHERE playthrough_id = %s AND command_id = ANY(%s)"
)
COMMAND_PAGE_DEFAULT_LIMIT = 50
COMMAND_PAGE_MAX_LIMIT = 200
CURSOR_SQL = """SELECT acceptance_sequence FROM simulation_commands
WHERE playthrough_id = %s AND actor_id = %s AND command_id = %s"""
LIST_SQL = """SELECT payload FROM simulation_commands
WHERE playthrough_id = %s AND actor_id = %s AND acceptance_sequence > %s
ORDER BY acceptance_sequence LIMIT %s"""


async def save_commands(
    connection: AsyncConnection,
    playthrough_id: UUID,
    commands: Sequence[AcceptedCommand],
) -> None:
    async with connection.cursor() as cursor:
        await cursor.executemany(
            UPSERT_SQL,
            [
                (
                    playthrough_id,
                    command.id,
                    command.actor_id,
                    command.operation_id,
                    command.faction_id,
                    command.battle_id,
                    command.accepted_turn,
                    command.accepted_wave,
                    command.execution_turn,
                    command.reserved_cost,
                    command.status.value,
                    command.failure_reason,
                    Jsonb(command.model_dump(mode="json")),
                )
                for command in commands
            ],
        )


async def delete_commands(
    connection: AsyncConnection, playthrough_id: UUID, command_ids: Sequence[str]
) -> None:
    if command_ids:
        await connection.execute(DELETE_SQL, (playthrough_id, list(command_ids)))


async def list_commands(
    connection: AsyncConnection,
    playthrough_id: UUID,
    actor_id: str,
    after_id: str = "",
    limit: int = COMMAND_PAGE_DEFAULT_LIMIT,
) -> list[AcceptedCommand]:
    sequence = await cursor_sequence(connection, playthrough_id, actor_id, after_id)
    cursor = await connection.execute(
        LIST_SQL,
        (
            playthrough_id,
            actor_id,
            sequence,
            min(max(limit, 1), COMMAND_PAGE_MAX_LIMIT),
        ),
    )
    return [AcceptedCommand.model_validate(row[0]) for row in await cursor.fetchall()]


async def cursor_sequence(
    connection: AsyncConnection, playthrough_id: UUID, actor_id: str, after_id: str
) -> int:
    if not after_id:
        return 0
    cursor = await connection.execute(CURSOR_SQL, (playthrough_id, actor_id, after_id))
    row = await cursor.fetchone()
    if row is None:
        raise CommandError("command cursor unavailable", "invalid_cursor", 422)
    return row[0]
