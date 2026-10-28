"""Repository for sim_playthrough. SQL lives only here."""

from uuid import UUID

from app.models.persistence import PlaythroughRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.scenario import StrategyScenario

INSERT_PLAYTHROUGH_SQL = """
INSERT INTO sim_playthrough (
    playthrough_id, owner_user_id, scenario, scenario_schema_version
)
VALUES (
    %(playthrough_id)s, %(owner_user_id)s, %(scenario)s, %(scenario_schema_version)s
)
ON CONFLICT (playthrough_id) DO NOTHING
RETURNING playthrough_id
"""

SELECT_PLAYTHROUGH_SQL = (
    "SELECT * FROM sim_playthrough WHERE playthrough_id = %(playthrough_id)s"
)


async def insert_playthrough(
    connection: AsyncConnection,
    playthrough_id: UUID,
    owner_user_id: UUID,
    scenario: StrategyScenario,
    scenario_schema_version: int,
) -> bool:
    cursor = await connection.execute(
        INSERT_PLAYTHROUGH_SQL,
        {
            "playthrough_id": playthrough_id,
            "owner_user_id": owner_user_id,
            "scenario": Jsonb(scenario.model_dump(mode="json")),
            "scenario_schema_version": scenario_schema_version,
        },
    )
    return await cursor.fetchone() is not None


async def get_playthrough(
    connection: AsyncConnection, playthrough_id: UUID
) -> PlaythroughRow | None:
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(SELECT_PLAYTHROUGH_SQL, {"playthrough_id": playthrough_id})
        return await cursor.fetchone()
