from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.succession import HealthBand
from tests.engine.succession.builders import SCENARIO, make_succession_world, tuned
from tests.services.helpers import mutation, seed_world

CERTAIN_DEATH = {band: 1000 for band in HealthBand}


async def _seed(db_connection: AsyncConnection) -> str:
    scenario = tuned(SCENARIO, death_per_mille=CERTAIN_DEATH, max_death_per_mille=1000)
    identity = await seed_world(db_connection, make_succession_world(), scenario)
    return f"/v1/playthroughs/{identity}"


async def _end_turn(api: AsyncClient, base: str) -> dict:
    state = (await api.get(f"{base}/world")).json()
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("end", state["world_version"], state["turn"]).model_dump(),
    )
    assert ended.status_code == 200
    return (await api.get(f"{base}/world")).json()


async def test_the_players_ruler_survives_a_deadly_turn(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    before = (await api.get(f"{base}/world")).json()["my_faction"]["leader_id"]

    view = await _end_turn(api, base)

    assert view["status"] == "planning"
    assert view["my_faction"]["leader_id"] == before


async def test_replay_verification_passes_across_a_succession(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    await _end_turn(api, base)

    verified = await api.post(f"{base}/replay/verify")

    assert verified.status_code == 200


async def test_no_ruler_age_or_health_appears_in_the_view(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)

    rivals = (await api.get(f"{base}/world")).json()["rivals"]

    for rival in rivals:
        assert "ruler_age" not in rival and "ruler_health" not in rival
    assert "ruler_age" not in (await api.get(f"{base}/world")).json()["my_faction"]
