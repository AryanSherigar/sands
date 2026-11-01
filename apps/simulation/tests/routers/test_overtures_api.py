from app.models.world_state import WorldState
from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.overtures.builders import (
    scenario_with,
    war_world,
)
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation, seed_world


async def _seed_war(db_connection: AsyncConnection) -> tuple[str, WorldState]:
    world = war_world(attacker_score=40)
    scenario = scenario_with(peace_offer_min_strain=0)
    identity = await seed_world(db_connection, world, scenario)
    return f"/v1/playthroughs/{identity}", world


async def _end_turn_into_overture(
    api: AsyncClient, db_connection: AsyncConnection
) -> tuple[str, dict, str]:
    base, _ = await _seed_war(db_connection)
    state = (await api.get(f"{base}/world")).json()
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("end", state["world_version"], state["turn"]).model_dump(),
    )
    assert ended.status_code == 200
    world = (await api.get(f"{base}/world")).json()
    assert world["status"] == "awaiting_scene"
    return base, world, world["scene_id"]


def _decision(operation: str, world: dict, is_confirmed: bool, sequence: int | None):
    body = mutation(operation, world["world_version"], world["turn"]).model_dump()
    return body | {"is_confirmed": is_confirmed, "proposal_sequence": sequence}


async def test_npc_peace_offer_arrives_as_a_scene_the_player_can_accept(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, world, scene_id = await _end_turn_into_overture(api, db_connection)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["initiator"] == "ai"
    assert view["scene_type"] == "peace"
    assert view["pending_proposal_sequence"] == 1

    accepted = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("accept", world, True, 1),
    )

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "planning"
    after = (await api.get(f"{base}/world")).json()
    assert len(after["truces"]) == 1


async def test_declining_an_npc_offer_keeps_the_war_and_the_cooldown(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, world, scene_id = await _end_turn_into_overture(api, db_connection)

    declined = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False, None),
    )

    assert declined.status_code == 200
    assert declined.json()["status"] == "planning"
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation(
            "next", declined.json()["world_version"], declined.json()["turn"]
        ).model_dump(),
    )
    assert ended.status_code == 200
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_replay_verification_passes_across_an_ignored_overture(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, world, scene_id = await _end_turn_into_overture(api, db_connection)
    await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False, None),
    )

    verified = await api.post(f"{base}/replay/verify")

    assert verified.status_code == 200


async def test_scene_view_shows_the_pretext_but_no_hidden_numbers(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id = await _end_turn_into_overture(api, db_connection)

    text = (await api.get(f"{base}/scenes/{scene_id}")).text

    assert "approaches" in text
    for hidden in ('"strain"', '"will"', "hidden_limits", "accept_at"):
        assert hidden not in text.lower()


async def test_a_peace_scene_gives_the_narrator_a_brief_the_player_never_sees(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id = await _end_turn_into_overture(api, db_connection)
    path = f"/internal/v1/scenes/{scene_id}"
    headers = {
        "X-Internal-Service-Token": "internal",
        "X-Acting-User-Id": str(OWNER_USER_ID),
    }

    package = (await api.get(f"{path}/package", headers=headers)).json()["package"]
    view = await api.get(f"{base}/scenes/{scene_id}")

    brief = package["hidden_limits"]["peace_brief"]
    assert brief["standing"] in {"leading", "even", "trailing"}
    assert {item["tier"] for item in brief["tiers"]} >= {"short", "perpetual"}
    assert "peace_brief" not in view.text
    assert "standing" not in view.text
