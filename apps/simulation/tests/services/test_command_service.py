import pytest
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus, DeceiveCommand
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from tests.engine.battles.builders import ATTACKER, DEFENDER
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation, seed_battle


async def test_applied_status_persists_and_original_command_response_stays_stable(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    campaign = CampaignService(db_connection)
    commands = CommandService(db_connection)
    await campaign.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    request = mutation("deceive", 2, wave=1)
    command = DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1")
    accepted = await commands.accept(identity, OWNER_USER_ID, request, command)
    await campaign.advance(
        identity, OWNER_USER_ID, mutation("advance", accepted.world_version, wave=1)
    )
    records = await commands.list_commands(identity, OWNER_USER_ID)
    assert len(records) == 1 and records[0].status == CommandStatus.APPLIED
    assert await commands.accept(identity, OWNER_USER_ID, request, command) == accepted
    with pytest.raises(CommandError, match="operation identity"):
        await campaign.advance(identity, OWNER_USER_ID, request)


async def test_foreign_faction_cannot_spend_or_read_hidden_commands(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    await CampaignService(db_connection).begin(
        identity, OWNER_USER_ID, mutation("begin", 1)
    )
    command = DeceiveCommand(faction_id=DEFENDER, battle_id="battle_1")
    with pytest.raises(CommandError) as error:
        await CommandService(db_connection).accept(
            identity, OWNER_USER_ID, mutation("foreign", 2, wave=1), command
        )
    assert error.value.status_code == 404
    assert (
        await CommandService(db_connection).list_commands(identity, OWNER_USER_ID) == []
    )


async def test_mutations_do_not_rewrite_unchanged_historical_commands(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    campaign = CampaignService(db_connection)
    commands = CommandService(db_connection)
    await campaign.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    command = DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1")
    await commands.accept(
        identity, OWNER_USER_ID, mutation("first", 2, wave=1), command
    )
    advanced = await campaign.advance(
        identity, OWNER_USER_ID, mutation("wave1", 3, wave=1)
    )
    await db_connection.execute("""CREATE FUNCTION task5_preserve_history() RETURNS trigger LANGUAGE plpgsql
        AS $$ BEGIN RAISE EXCEPTION 'unchanged historical command rewritten'; END $$""")
    await db_connection.execute("""CREATE TRIGGER task5_history BEFORE UPDATE ON simulation_commands
        FOR EACH ROW WHEN (OLD.status = 'applied' AND NEW.status = 'applied') EXECUTE FUNCTION task5_preserve_history()""")
    try:
        await commands.accept(
            identity,
            OWNER_USER_ID,
            mutation("second", advanced.world_version, wave=2),
            command,
        )
    finally:
        await db_connection.execute("DROP TRIGGER task5_history ON simulation_commands")
        await db_connection.execute("DROP FUNCTION task5_preserve_history()")


async def test_command_cursor_keeps_later_acceptance_with_smaller_uuid(
    db_connection: AsyncConnection,
) -> None:
    from app.repositories import command_repo
    from tests.engine.battles.builders import command

    identity = await seed_battle(db_connection)
    payload = DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1")
    first_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    later_id = "00000000-0000-0000-0000-000000000001"
    first = command(payload, identity=first_id).model_copy(
        update={"actor_id": str(OWNER_USER_ID)}
    )
    later = command(payload, identity=later_id).model_copy(
        update={"actor_id": str(OWNER_USER_ID)}
    )
    await command_repo.save_commands(db_connection, identity, [first])
    service = CommandService(db_connection)
    assert [
        row.id for row in await service.list_commands(identity, OWNER_USER_ID, limit=1)
    ] == [first_id]
    await command_repo.save_commands(db_connection, identity, [later])
    page = await service.list_commands(identity, OWNER_USER_ID, after_id=first_id)
    assert [row.id for row in page] == [later_id]
