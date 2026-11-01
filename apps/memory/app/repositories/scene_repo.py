"""Repository for memory_scene_state."""

from uuid import UUID

from app.models.facts import SceneStateCreate, SceneStateRow
from psycopg import AsyncConnection
from psycopg.rows import class_row

APPEND_SCENE_STATE_SQL = """
INSERT INTO memory_scene_state (
    playthrough_id, valid_from_seq, location_entity_id, present_entity_ids, extraction_batch_id
) VALUES (
    %(playthrough_id)s, %(valid_from_seq)s, %(location_entity_id)s,
    %(present_entity_ids)s, %(extraction_batch_id)s
)
ON CONFLICT (playthrough_id, valid_from_seq) DO NOTHING
RETURNING *
"""

SELECT_SCENE_STATE_SQL = """
SELECT * FROM memory_scene_state
WHERE playthrough_id = %(playthrough_id)s AND valid_from_seq = %(valid_from_seq)s
"""

GET_SCENE_AT_SQL = """
SELECT * FROM memory_scene_state
WHERE playthrough_id = %(playthrough_id)s AND valid_from_seq <= %(at_seq)s
ORDER BY valid_from_seq DESC
LIMIT 1
"""


async def append_scene_state(
    connection: AsyncConnection, scene: SceneStateCreate
) -> SceneStateRow:
    async with connection.cursor(row_factory=class_row(SceneStateRow)) as cursor:
        await cursor.execute(APPEND_SCENE_STATE_SQL, scene.model_dump())
        row = await cursor.fetchone()
        if row is not None:
            return row
        await cursor.execute(
            SELECT_SCENE_STATE_SQL,
            {
                "playthrough_id": scene.playthrough_id,
                "valid_from_seq": scene.valid_from_seq,
            },
        )
        existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError(
            "Scene state insert conflicted but no existing row was found."
        )
    return existing


async def get_scene_at(
    connection: AsyncConnection, playthrough_id: UUID, at_seq: int
) -> SceneStateRow | None:
    async with connection.cursor(row_factory=class_row(SceneStateRow)) as cursor:
        await cursor.execute(
            GET_SCENE_AT_SQL, {"playthrough_id": playthrough_id, "at_seq": at_seq}
        )
        return await cursor.fetchone()
