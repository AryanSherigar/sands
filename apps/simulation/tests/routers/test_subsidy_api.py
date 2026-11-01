from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.services.helpers import mutation, seed_world

INSTALMENT = 10
DURATION = 4


async def _seed(db_connection: AsyncConnection) -> str:
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)
    identity = await seed_world(db_connection, world, SCENARIO)
    return f"/v1/playthroughs/{identity}"


def _guard(operation_id: str, state: dict) -> dict:
    return mutation(operation_id, state["world_version"], state["turn"]).model_dump()


async def _world(api: AsyncClient, base: str) -> dict:
    return (await api.get(f"{base}/world")).json()


async def _queue(api: AsyncClient, base: str, name: str, command: dict) -> None:
    state = await _world(api, base)
    queued = await api.post(
        f"{base}/commands", json=_guard(name, state) | {"command": command}
    )
    assert queued.status_code == 200, queued.text


async def _end_turn(api: AsyncClient, base: str, name: str) -> None:
    state = await _world(api, base)
    ended = await api.post(f"{base}/end-turn", json=_guard(name, state))
    assert ended.status_code == 200, ended.text


async def test_a_subsidy_is_paid_cut_and_visible_in_the_world_view(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    await _queue(
        api,
        base,
        "grant",
        {
            "kind": "subsidize",
            "faction_id": PLAYER,
            "target_faction_id": CAUTIOUS_RIVAL,
            "war_id": "war_1",
            "amount_per_turn": INSTALMENT,
            "turns": DURATION,
        },
    )
    await _end_turn(api, base, "end-1")

    [subsidy] = (await _world(api, base))["subsidies"]
    assert subsidy["receiver_id"] == CAUTIOUS_RIVAL
    assert subsidy["turns_left"] == DURATION - 1

    await _queue(
        api,
        base,
        "cut",
        {"kind": "cut_subsidy", "faction_id": PLAYER, "subsidy_id": subsidy["id"]},
    )
    await _end_turn(api, base, "end-2")

    view = await _world(api, base)
    assert view["subsidies"] == []


async def test_replay_verification_passes_across_a_subsidy_and_a_disaster(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    await _queue(
        api,
        base,
        "grant",
        {
            "kind": "subsidize",
            "faction_id": PLAYER,
            "target_faction_id": CAUTIOUS_RIVAL,
            "war_id": "war_1",
            "amount_per_turn": INSTALMENT,
            "turns": DURATION,
        },
    )
    await _end_turn(api, base, "end-1")
    await _end_turn(api, base, "end-2")

    verified = await api.post(f"{base}/replay/verify")

    assert verified.status_code == 200
