"""Repository for scenes. SQL lives only here."""

from uuid import UUID

from app.exceptions.scene_exceptions import InvalidSceneTransitionError
from app.models.persistence import SceneRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.scene import SceneOutcome, ScenePackage, SceneStatus

FINAL_STATUSES = (SceneStatus.RESOLVED, SceneStatus.DEFAULTED)

INSERT_SCENE_SQL = """
INSERT INTO scenes (scene_id, playthrough_id, scene_type, status, turn, package)
VALUES (%(scene_id)s, %(playthrough_id)s, %(scene_type)s, 'pending', %(turn)s, %(package)s)
ON CONFLICT (scene_id) DO NOTHING
RETURNING scene_id
"""

SELECT_SCENE_SQL = "SELECT * FROM scenes WHERE scene_id = %(scene_id)s"

SELECT_OPEN_SCENE_SQL = """
SELECT * FROM scenes
WHERE playthrough_id = %(playthrough_id)s AND status IN ('pending', 'opened')
ORDER BY created_at DESC
LIMIT 1
"""

MARK_SCENE_OPENED_SQL = """
UPDATE scenes SET status = 'opened'
WHERE scene_id = %(scene_id)s AND status = 'pending'
RETURNING scene_id
"""

RESOLVE_SCENE_SQL = """
UPDATE scenes
SET status = %(status)s, outcome = %(outcome)s, resolved_at = now()
WHERE scene_id = %(scene_id)s AND status IN ('pending', 'opened')
RETURNING scene_id
"""


RECORD_FAILED_ATTEMPT_SQL = """
UPDATE scenes SET failed_attempts = failed_attempts + 1
WHERE scene_id = %(scene_id)s AND status IN ('pending', 'opened')
RETURNING failed_attempts
"""

RESET_FAILED_ATTEMPTS_SQL = """
UPDATE scenes SET failed_attempts = 0
WHERE scene_id = %(scene_id)s AND failed_attempts > 0
"""


async def insert_scene(connection: AsyncConnection, package: ScenePackage) -> bool:
    cursor = await connection.execute(
        INSERT_SCENE_SQL,
        {
            "scene_id": package.scene_id,
            "playthrough_id": package.playthrough_id,
            "scene_type": package.scene_type.value,
            "turn": package.turn,
            "package": Jsonb(package.model_dump(mode="json")),
        },
    )
    return await cursor.fetchone() is not None


async def _fetch_scene(
    connection: AsyncConnection, query: str, parameters: dict[str, object]
) -> SceneRow | None:
    async with connection.cursor(row_factory=class_row(SceneRow)) as cursor:
        await cursor.execute(query, parameters)
        return await cursor.fetchone()


async def get_scene(connection: AsyncConnection, scene_id: UUID) -> SceneRow | None:
    return await _fetch_scene(connection, SELECT_SCENE_SQL, {"scene_id": scene_id})


async def get_open_scene(
    connection: AsyncConnection, playthrough_id: UUID
) -> SceneRow | None:
    return await _fetch_scene(
        connection, SELECT_OPEN_SCENE_SQL, {"playthrough_id": playthrough_id}
    )


async def mark_scene_opened(connection: AsyncConnection, scene_id: UUID) -> bool:
    cursor = await connection.execute(MARK_SCENE_OPENED_SQL, {"scene_id": scene_id})
    return await cursor.fetchone() is not None


async def resolve_scene(
    connection: AsyncConnection,
    scene_id: UUID,
    status: SceneStatus,
    outcome: SceneOutcome,
) -> bool:
    if status not in FINAL_STATUSES:
        raise InvalidSceneTransitionError(status.value)
    cursor = await connection.execute(
        RESOLVE_SCENE_SQL,
        {
            "scene_id": scene_id,
            "status": status.value,
            "outcome": Jsonb(outcome.model_dump(mode="json")),
        },
    )
    return await cursor.fetchone() is not None


async def record_failed_attempt(
    connection: AsyncConnection, scene_id: UUID
) -> int | None:
    cursor = await connection.execute(RECORD_FAILED_ATTEMPT_SQL, {"scene_id": scene_id})
    row = await cursor.fetchone()
    return None if row is None else int(row[0])


async def reset_failed_attempts(connection: AsyncConnection, scene_id: UUID) -> None:
    await connection.execute(RESET_FAILED_ATTEMPTS_SQL, {"scene_id": scene_id})
