from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.pressure.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.services.helpers import mutation, seed_world


async def _seed(db_connection: AsyncConnection) -> str:
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    identity = await seed_world(db_connection, world, SCENARIO)
    return f"/v1/playthroughs/{identity}"


async def _state(api: AsyncClient, base: str) -> dict:
    return (await api.get(f"{base}/world")).json()


async def test_a_mobilization_is_ordered_shown_and_replays(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    assert (await _state(api, base))["mobilization"] is None
    state = await _state(api, base)
    guard = mutation("mobilize", state["world_version"], state["turn"]).model_dump()
    queued = await api.post(
        f"{base}/commands",
        json=guard | {"command": {"kind": "mobilize", "faction_id": PLAYER}},
    )
    assert queued.status_code == 200, queued.text

    state = await _state(api, base)
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("end", state["world_version"], state["turn"]).model_dump(),
    )
    assert ended.status_code == 200, ended.text

    assert (await _state(api, base))["mobilization"]["turns_left"] >= 1
    assert (await api.post(f"{base}/replay/verify")).status_code == 200


async def test_mobilizing_while_at_peace_is_rejected(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_world(db_connection, make_world(), SCENARIO)
    base = f"/v1/playthroughs/{identity}"
    state = await _state(api, base)
    guard = mutation("mobilize", state["world_version"], state["turn"]).model_dump()

    rejected = await api.post(
        f"{base}/commands",
        json=guard | {"command": {"kind": "mobilize", "faction_id": PLAYER}},
    )

    assert rejected.status_code == 422
    assert rejected.json()["code"] == "not_at_war"
