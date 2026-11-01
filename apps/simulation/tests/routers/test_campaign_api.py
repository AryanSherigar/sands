from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.economy.builders import make_scenario
from tests.engine.economy.test_shortfall import _world
from tests.middleware.helpers import make_token
from tests.services.helpers import mutation, seed_battle, seed_world
from tests.services.test_campaign_service import initialization


async def test_initialize_world_identity_and_auth(api: AsyncClient) -> None:
    request = initialization().model_dump(mode="json")
    endpoint = "/internal/v1/playthroughs"
    assert (await api.post(endpoint, json=request)).status_code == 401
    headers = {"X-Internal-Service-Token": "internal"}
    initial = await api.post(endpoint, json=request, headers=headers)
    assert initial.status_code == 200
    assert (
        await api.post(endpoint, json=request, headers=headers)
    ).json() == initial.json()
    conflict = await api.post(endpoint, json=request | {"seed": 99}, headers=headers)
    assert conflict.status_code == 409
    path = f"/v1/playthroughs/{request['playthrough_id']}/world"
    world = await api.get(path)
    assert world.status_code == 200
    assert world.json()["world_version"] == 1
    assert "manpower" in world.json()["my_faction"]
    assert "manpower_pool" not in world.text
    assert (
        await api.get(path, headers={"Authorization": "Bearer invalid"})
    ).status_code == 401
    assert (await api.get(f"/v1/playthroughs/{uuid4()}/world")).status_code == 404


async def test_historical_world_and_replay_verification(api: AsyncClient) -> None:
    request = initialization().model_dump(mode="json")
    headers = {"X-Internal-Service-Token": "internal"}
    initial = await api.post("/internal/v1/playthroughs", json=request, headers=headers)
    base = f"/v1/playthroughs/{request['playthrough_id']}"
    command = {
        "operation_id": "tax",
        "expected_world_version": initial.json()["world_version"],
        "expected_turn": 0,
        "expected_wave": 0,
        "command": {
            "kind": "set_tax_rate",
            "faction_id": "house_carrow",
            "tax_rate": "high",
        },
    }
    accepted = await api.post(f"{base}/commands", json=command)
    await api.post(
        f"{base}/end-turn",
        json=mutation("begin", accepted.json()["world_version"]).model_dump(),
    )
    history = await api.get(f"{base}/history/0")
    verified = await api.post(f"{base}/replay/verify?through_turn=1")
    assert history.status_code == verified.status_code == 200
    assert history.json()["world"]["clock"]["turn"] == 0
    assert verified.json()["verified_turn"] == 1
    assert "rng" not in history.text


async def test_wave_retry_and_battle_read_surface(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_battle(db_connection, orders=0)
    base = f"/v1/playthroughs/{identity}"
    page = await api.get(f"{base}/battles?limit=1")
    assert page.status_code == 200
    battle_id = page.json()["items"][0]["id"]
    assert (await api.get(f"{base}/battles/{battle_id}")).status_code == 200
    assert (await api.get(f"{base}/battles/unknown")).status_code == 404
    opened = await api.post(f"{base}/end-turn", json=mutation("begin", 1).model_dump())
    assert opened.status_code == 200 and opened.json()["status"] == "awaiting_commands"
    body = mutation("wave", opened.json()["world_version"], wave=1).model_dump()
    first = await api.post(f"{base}/battles/advance", json=body)
    assert first.status_code == 200
    assert (await api.post(f"{base}/battles/advance", json=body)).json() == first.json()
    stale = await api.post(
        f"{base}/battles/advance", json=body | {"operation_id": "other"}
    )
    assert stale.status_code == 409
    reports = await api.get(f"{base}/battles/{battle_id}/reports?limit=1")
    assert reports.status_code == 200 and len(reports.json()["items"]) == 1
    assert "input_hash" not in reports.text and "accounting" not in reports.text
    assert (await api.get(f"{base}/battles?limit=201")).status_code == 422
    assert (await api.get(f"{base}/battles?after_id=unknown")).status_code == 422


async def test_foreign_and_unknown_resources_match_and_battle_views_are_redacted(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_battle(db_connection)
    base = f"/v1/playthroughs/{identity}"
    outsider = {"Authorization": f"Bearer {make_token(sub=str(uuid4()))}"}
    foreign = await api.get(f"{base}/world", headers=outsider)
    missing = await api.get(f"/v1/playthroughs/{uuid4()}/world", headers=outsider)
    assert (foreign.status_code, foreign.content) == (
        missing.status_code,
        missing.content,
    )
    forbidden_begin = await api.post(
        f"{base}/end-turn", json=mutation("outsider", 1).model_dump(), headers=outsider
    )
    missing_begin = await api.post(
        f"/v1/playthroughs/{uuid4()}/end-turn",
        json=mutation("outsider", 1).model_dump(),
        headers=outsider,
    )
    assert (forbidden_begin.status_code, forbidden_begin.content) == (
        missing_begin.status_code,
        missing_begin.content,
    )
    detail = await api.get(f"{base}/battles/battle_1")
    report = await api.get(f"{base}/battles/battle_1/reports?limit=1")
    assert detail.status_code == report.status_code == 200
    for response in (detail, report):
        for hidden_field in (
            "actual_troops",
            "actual_strength",
            "accepted_commands",
            "accounting",
            "input_hash",
            "rng",
            "truth",
            "pending_intent",
        ):
            assert hidden_field not in response.text


@pytest.mark.parametrize("choice", ["shortfall_take_loan", "shortfall_default"])
async def test_economy_choice_api(
    api: AsyncClient, db_connection: AsyncConnection, choice: str
) -> None:
    identity = await seed_world(db_connection, _world(), make_scenario())
    base = f"/v1/playthroughs/{identity}"
    paused = await api.post(f"{base}/end-turn", json=mutation("begin", 1).model_dump())
    assert paused.status_code == 200 and paused.json()["status"] == "awaiting_scene"
    path = f"{base}/scenes/{paused.json()['scene_id']}/choice"
    body = mutation("choice", paused.json()["world_version"]).model_dump()
    assert (await api.post(path, json=body | {"choice": "cheat"})).status_code == 422
    completed = await api.post(path, json=body | {"choice": choice})
    assert completed.status_code == 200 and completed.json()["turn"] == 1
    assert (
        await api.post(path, json=body | {"choice": choice})
    ).json() == completed.json()
