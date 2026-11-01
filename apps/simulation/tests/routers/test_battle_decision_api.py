from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.battles.builders import ATTACKER, battle_fixture, start_battle
from tests.services.helpers import mutation, seed_world


async def _new_battle_base(db_connection: AsyncConnection) -> str:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    start_battle(world, scenario)
    identity = await seed_world(db_connection, world, scenario)
    return f"/v1/playthroughs/{identity}"


async def test_checkpoint_reload_choice_retry_advance_and_replay(
    api: AsyncClient,
    db_connection: AsyncConnection,
) -> None:
    base = await _new_battle_base(db_connection)
    opened = await api.post(f"{base}/end-turn", json=mutation("begin", 1).model_dump())
    assert opened.status_code == 200
    assert opened.json()["status"] == "awaiting_battle_decision"
    loaded = await api.get(f"{base}/world")
    assert loaded.json()["status"] == "awaiting_battle_decision"
    blocked = await api.post(
        f"{base}/battles/advance", json=mutation("blocked", 2, wave=1).model_dump()
    )
    assert blocked.status_code == 409
    body = mutation("choice", 2, wave=1).model_dump() | {
        "command": {
            "kind": "take_command",
            "battle_id": "battle_1",
            "faction_id": ATTACKER,
        }
    }
    chosen = await api.post(f"{base}/commands", json=body)
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["status"] == "awaiting_commands"
    assert chosen.json()["battles"][0]["total_exchanges"] == 0
    assert (await api.post(f"{base}/commands", json=body)).json() == chosen.json()
    await _finish_and_verify(api, base, chosen.json()["world_version"])


async def _finish_and_verify(api: AsyncClient, base: str, version: int) -> None:
    for wave in range(1, 5):
        result = await api.post(
            f"{base}/battles/advance",
            json=mutation(f"wave{wave}", version, wave=wave).model_dump(),
        )
        assert result.status_code == 200, result.text
        version = result.json()["world_version"]
    assert result.json()["status"] == "turn_completed"
    verified = await api.post(f"{base}/replay/verify?through_turn=1")
    assert verified.status_code == 200, verified.text


async def test_delegated_waves_persist_and_replay_in_one_transition(
    api: AsyncClient,
    db_connection: AsyncConnection,
) -> None:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    start_battle(world, scenario)
    identity = await seed_world(db_connection, world, scenario)
    base = f"/v1/playthroughs/{identity}"
    await api.post(f"{base}/end-turn", json=mutation("begin", 1).model_dump())
    choice = mutation("delegate", 2, wave=1).model_dump() | {
        "command": {
            "kind": "delegate_battle",
            "battle_id": "battle_1",
            "faction_id": ATTACKER,
        }
    }
    selected = await api.post(f"{base}/commands", json=choice)
    assert selected.status_code == 200, selected.text
    body = mutation("auto", selected.json()["world_version"], wave=1).model_dump()
    completed = await api.post(f"{base}/battles/advance", json=body)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "turn_completed"
    assert (
        await api.post(f"{base}/battles/advance", json=body)
    ).json() == completed.json()
    reports = await api.get(f"{base}/battles/battle_1/reports")
    assert len(reports.json()["items"]) == 4
    verified = await api.post(f"{base}/replay/verify?through_turn=1")
    assert verified.status_code == 200, verified.text


async def test_ai_only_campaign_persists_automatic_receipts_on_end_turn(
    api: AsyncClient,
    db_connection: AsyncConnection,
) -> None:
    from tests.services.helpers import table_counts

    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    world.factions[ATTACKER].is_player = False
    world.factions["house_c"].is_player = True
    start_battle(world, scenario)
    identity = await seed_world(db_connection, world, scenario)
    base = f"/v1/playthroughs/{identity}"
    completed = await api.post(
        f"{base}/end-turn", json=mutation("begin", 1).model_dump()
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "turn_completed"
    assert (await table_counts(db_connection))["battle_exchanges"] == 4
    verified = await api.post(f"{base}/replay/verify?through_turn=1")
    assert verified.status_code == 200, verified.text
