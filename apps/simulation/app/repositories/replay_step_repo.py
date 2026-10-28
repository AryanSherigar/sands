"""Repository for append-only simulation replay steps."""

from uuid import UUID

from app.models.replay import ReplayStep
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

INSERT_STEP_SQL = """
INSERT INTO simulation_replay_steps
(playthrough_id, sequence, operation_id, kind, input, before_hash, after_hash, turn, wave)
VALUES (%(playthrough_id)s, %(sequence)s, %(operation_id)s, %(kind)s, %(input)s,
        %(before_hash)s, %(after_hash)s, %(turn)s, %(wave)s)
"""
SELECT_STEPS_SQL = """
SELECT playthrough_id, sequence, operation_id, kind, input, before_hash, after_hash, turn, wave
FROM simulation_replay_steps
WHERE playthrough_id = %(playthrough_id)s
ORDER BY sequence
"""
NEXT_SEQUENCE_SQL = """
SELECT COALESCE(MAX(sequence), 0) + 1 AS sequence
FROM simulation_replay_steps
WHERE playthrough_id = %(playthrough_id)s
"""


async def insert_step(connection: AsyncConnection, step: ReplayStep) -> None:
    await connection.execute(
        INSERT_STEP_SQL,
        {
            "playthrough_id": step.playthrough_id,
            "sequence": step.sequence,
            "operation_id": step.operation_id,
            "kind": step.kind.value,
            "input": Jsonb(step.input.model_dump(mode="json")),
            "before_hash": step.before_hash,
            "after_hash": step.after_hash,
            "turn": step.turn,
            "wave": step.wave,
        },
    )


async def list_steps(
    connection: AsyncConnection, playthrough_id: UUID
) -> list[ReplayStep]:
    async with connection.cursor(row_factory=class_row(ReplayStep)) as cursor:
        await cursor.execute(SELECT_STEPS_SQL, {"playthrough_id": playthrough_id})
        return await cursor.fetchall()


async def next_sequence(connection: AsyncConnection, playthrough_id: UUID) -> int:
    cursor = await connection.execute(
        NEXT_SEQUENCE_SQL, {"playthrough_id": playthrough_id}
    )
    return (await cursor.fetchone())[0]
