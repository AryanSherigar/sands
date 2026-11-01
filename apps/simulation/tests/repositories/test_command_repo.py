import pytest
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import AcceptedCommand, CommandStatus, DeceiveCommand
from app.repositories import command_repo
from psycopg import AsyncConnection

from tests.engine.battles.builders import ATTACKER, command
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import seed_battle


def accepted(identity: str, actor_id: str = str(OWNER_USER_ID)) -> AcceptedCommand:
    payload = DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1")
    return command(payload, identity=identity).model_copy(update={"actor_id": actor_id})


async def test_command_page_default_and_maximum_limits(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    await command_repo.save_commands(
        db_connection, identity, [accepted(str(index)) for index in range(205)]
    )
    default_page = await command_repo.list_commands(
        db_connection, identity, str(OWNER_USER_ID)
    )
    maximum_page = await command_repo.list_commands(
        db_connection, identity, str(OWNER_USER_ID), limit=999
    )
    assert len(default_page) == 50 and len(maximum_page) == 200


async def test_command_update_preserves_acceptance_cursor(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    records = [accepted(str(index)) for index in range(3)]
    await command_repo.save_commands(db_connection, identity, records)
    initial_sequence = await command_repo.cursor_sequence(
        db_connection, identity, str(OWNER_USER_ID), "0"
    )
    applied = records[0].model_copy(update={"status": CommandStatus.APPLIED})
    await command_repo.save_commands(db_connection, identity, [applied])
    updated_sequence = await command_repo.cursor_sequence(
        db_connection, identity, str(OWNER_USER_ID), "0"
    )
    assert updated_sequence == initial_sequence
    page = await command_repo.list_commands(
        db_connection, identity, str(OWNER_USER_ID), after_id="0", limit=2
    )
    assert [row.id for row in page] == ["1", "2"]


async def test_cursor_scope_rejects_foreign_actor_and_playthrough(
    db_connection: AsyncConnection,
) -> None:
    first = await seed_battle(db_connection)
    second = await seed_battle(db_connection)
    await command_repo.save_commands(db_connection, first, [accepted("private-cursor")])
    for identity, actor in ((first, "another-actor"), (second, str(OWNER_USER_ID))):
        with pytest.raises(CommandError, match="cursor unavailable"):
            await command_repo.list_commands(
                db_connection, identity, actor, after_id="private-cursor"
            )
