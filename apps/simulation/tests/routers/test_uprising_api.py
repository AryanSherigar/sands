from app.models.world_internal import UprisingState
from app.repositories import event_log_repo
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.scenario import StrategyScenario
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)
from tests.services.helpers import mutation, seed_world


async def test_uprising_resolution_is_durable_and_idempotent(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)],
        factions=[make_faction(PLAYER, is_player=True)],
    )
    world.internal_ruleset = 1
    world.uprisings = [
        UprisingState(
            id="uprising_home_0",
            region_id=HOME,
            faction_id=PLAYER,
            started_turn=0,
            trigger_unrest=80,
            income_penalty_percent=50,
            manpower_penalty_percent=50,
            supply_penalty_percent=50,
        )
    ]
    identity = await seed_world(db_connection, world, StrategyScenario())
    base = f"/v1/playthroughs/{identity}"
    payload = mutation("resolve", 1).model_dump() | {
        "command": {
            "kind": "resolve_uprising",
            "faction_id": PLAYER,
            "uprising_id": "uprising_home_0",
            "response": "concessions",
        }
    }

    first = await api.post(f"{base}/commands", json=payload)
    second = await api.post(f"{base}/commands", json=payload)

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert first.json()["world_version"] == 2
    events = await event_log_repo.list_events(db_connection, identity)
    assert [(event.seq, event.kind) for event in events] == [(1, "uprising_resolved")]


async def test_summary_request_is_materialized_atomically_with_immediate_response(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)],
        factions=[make_faction(PLAYER, is_player=True)],
    )
    world.internal_ruleset = 1
    world.summary_ruleset = 2
    world.uprisings = [
        UprisingState(
            id="uprising_home_0",
            region_id=HOME,
            faction_id=PLAYER,
            started_turn=0,
            trigger_unrest=80,
            income_penalty_percent=50,
            manpower_penalty_percent=50,
            supply_penalty_percent=50,
        )
    ]
    identity = await seed_world(db_connection, world, StrategyScenario())
    payload = mutation("resolve-summary", 1).model_dump() | {
        "command": {
            "kind": "resolve_uprising",
            "faction_id": PLAYER,
            "uprising_id": "uprising_home_0",
            "response": "concessions",
        }
    }
    base = f"/v1/playthroughs/{identity}"
    assert (await api.post(base + "/commands", json=payload)).status_code == 200
    assert (await api.post(base + "/commands", json=payload)).status_code == 200
    summaries = (await api.get(base + "/summaries")).json()["items"]
    assert len(summaries) == 1 and summaries[0]["trigger"] == "major_event"
    from app.repositories.summary_delivery_repo import availability

    assert (await availability(db_connection, identity)).pending_count == 1
