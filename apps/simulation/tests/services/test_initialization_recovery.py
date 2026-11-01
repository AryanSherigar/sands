import asyncio
from uuid import uuid4

import pytest
from app.exceptions.command_exceptions import CommandError
from app.models.battle_progress import InitializeCampaign, MutationResponse
from app.services.campaign_service import CampaignService
from psycopg import AsyncConnection
from psycopg.errors import RaiseException
from tests.services.helpers import install_failure, remove_failure, table_counts
from tests.services.test_campaign_service import initialization


async def _initialize(
    database_url: str, request: InitializeCampaign
) -> MutationResponse:
    async with await AsyncConnection.connect(
        database_url, autocommit=True
    ) as connection:
        return await CampaignService(connection).initialize(request)


async def test_concurrent_initialization_and_original_identity(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    await db_connection.set_autocommit(True)
    request = initialization()
    results = await asyncio.gather(
        *[_initialize(migrated_test_database_url, request) for _ in range(2)]
    )
    assert results[0] == results[1]
    counts = await table_counts(db_connection)
    assert (
        counts["world_state"]
        == counts["world_snapshots"]
        == counts["simulation_operations"]
        == 1
    )
    for field, changed in [
        ("owner_user_id", uuid4()),
        ("seed", 43),
        ("player_faction_id", "house_ashford"),
    ]:
        with pytest.raises(CommandError, match="identity"):
            await CampaignService(db_connection).initialize(
                request.model_copy(update={field: changed})
            )
    same_identity = request.model_copy(update={"operation_id": "another-init"})
    assert (
        await CampaignService(db_connection).initialize(same_identity)
    ).world_hash == results[0].world_hash


@pytest.mark.parametrize(
    "table", ["world_state", "world_snapshots", "simulation_operations"]
)
async def test_initialization_failures_rollback_parent_and_snapshot(
    db_connection: AsyncConnection, table: str
) -> None:
    await db_connection.set_autocommit(True)
    request = initialization()
    await install_failure(db_connection, table)
    try:
        with pytest.raises(RaiseException):
            await CampaignService(db_connection).initialize(request)
    finally:
        await remove_failure(db_connection, table)
    counts = await table_counts(db_connection)
    assert all(value == 0 for value in counts.values())
    cursor = await db_connection.execute("SELECT count(*) FROM sim_playthrough")
    assert await cursor.fetchone() == (0,)
    assert (await CampaignService(db_connection).initialize(request)).world_version == 1
