"""Integration tests for the playtest and duplicate scenario endpoints."""

import json
import uuid
from pathlib import Path

import pytest
from app.db.models.playthrough import Playthrough
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.scenario import StrategyScenario

TRACED_MAP_PATH = (
    Path(__file__).parents[4]
    / "packages"
    / "strategy-contracts"
    / "tests"
    / "traced_map.json"
)


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
async def dev_user2(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev User 2"
    )


@pytest.fixture
async def master_scenario_id(async_client: AsyncClient, dev_user) -> str:
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Hollow Cairn",
            "mode": "master",
            "complexity_tier": "master",
        },
        headers=headers,
    )
    scenario_id = response.json()["scenario_id"]
    await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={
            "state_schema": {
                "player": {"type": "object", "fields": {"health": {"type": "number"}}}
            }
        },
        headers=headers,
    )
    return scenario_id


async def _seed_master_world(
    async_client: AsyncClient, headers: dict, scenario_id: str
) -> dict[str, str]:
    """Create entities, facts, conditions, entity types, maps, pins,
    connections, and minigames on scenario_id, returning their IDs for assertions."""
    entity_type_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entity-types",
        json={
            "type_key": "artifact",
            "display_label": "Magical Artifact",
            "attributes_schema": {"power": {"type": "number"}},
        },
        headers=headers,
    )
    warden_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "character", "canonical_name": "The Warden"},
        headers=headers,
    )
    cairn_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "location", "canonical_name": "Hollow Cairn"},
        headers=headers,
    )
    crypt_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "location", "canonical_name": "Forgotten Crypt"},
        headers=headers,
    )
    warden_id = warden_resp.json()["entity_id"]
    cairn_id = cairn_resp.json()["entity_id"]
    crypt_id = crypt_resp.json()["entity_id"]

    fact_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/facts",
        json={
            "subject_entity_id": warden_id,
            "predicate": "guards",
            "object_entity_id": cairn_id,
        },
        headers=headers,
    )
    condition_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/conditions",
        json={
            "label": "Warden Is Wary",
            "condition_expression": {
                "field": "player.health",
                "op": ">=",
                "value": 0,
            },
            "narrator_instruction": "The Warden watches.",
        },
        headers=headers,
    )
    end_condition_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/end_conditions",
        json={
            "condition_expression": {"field": "player.health", "op": "<=", "value": 0},
            "outcome_tag": "lose",
            "outcome_title": "Consumed",
            "outcome_text": "Ashfall waits.",
        },
        headers=headers,
    )
    invariant_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/invariants",
        json={
            "label": "Health cannot go negative",
            "invariant_expression": {
                "field": "player.health",
                "op": ">=",
                "value": 0,
            },
            "applies_to": "global",
            "narrator_text": "Health cannot fall below zero.",
        },
        headers=headers,
    )
    map_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/maps",
        json={"name": "Upper Realm", "display_order": 0},
        headers=headers,
    )
    map_id = map_resp.json()["map_id"]

    pin1_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/maps/{map_id}/pins",
        json={
            "entity_id": cairn_id,
            "x": 0.2,
            "y": 0.4,
            "is_start_location": True,
        },
        headers=headers,
    )
    pin2_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/maps/{map_id}/pins",
        json={
            "entity_id": crypt_id,
            "x": 0.6,
            "y": 0.8,
            "is_start_location": False,
        },
        headers=headers,
    )
    conn_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/map-connections",
        json={
            "entity_id_a": cairn_id,
            "entity_id_b": crypt_id,
            "label": "Stone Bridge",
        },
        headers=headers,
    )
    minigame_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/minigames",
        json={
            "label": "Dodge Falling Rocks",
            "minigame_type": "dodge",
            "dodge_config": {"difficulty": 3},
            "outcome_mode": "binary",
            "win_mutation": {"path": "player.health", "op": "set", "value": 100},
            "lose_mutation": {"path": "player.health", "op": "decrement", "value": 15},
        },
        headers=headers,
    )

    return {
        "entity_type_id": entity_type_resp.json()["scenario_entity_type_id"],
        "warden_id": warden_id,
        "cairn_id": cairn_id,
        "crypt_id": crypt_id,
        "fact_id": fact_resp.json()["fact_id"],
        "condition_id": condition_resp.json()["condition_id"],
        "end_condition_id": end_condition_resp.json()["end_condition_id"],
        "invariant_id": invariant_resp.json()["invariant_id"],
        "map_id": map_id,
        "pin1_id": pin1_resp.json()["pin_id"],
        "pin2_id": pin2_resp.json()["pin_id"],
        "connection_id": conn_resp.json()["connection_id"],
        "minigame_id": minigame_resp.json()["minigame_id"],
    }


@pytest.mark.asyncio
async def test_playtest_creates_is_playtest_playthrough(
    async_client: AsyncClient,
    dev_user,
    master_scenario_id: str,
    db_session: AsyncSession,
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/playtest", headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["is_playtest"] is True
    assert data["scenario_id"] == master_scenario_id

    stmt = select(Playthrough).where(
        Playthrough.playthrough_id == uuid.UUID(data["playthrough_id"])
    )
    playthrough = (await db_session.execute(stmt)).scalars().first()
    assert playthrough is not None
    assert playthrough.is_playtest is True


@pytest.mark.asyncio
async def test_playtest_rejects_non_owner(
    async_client: AsyncClient, dev_user2, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user2.user_id)}
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/playtest", headers=headers
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_playtest_excluded_from_rating_eligibility(
    async_client: AsyncClient,
    dev_user,
    master_scenario_id: str,
    db_session: AsyncSession,
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/playtest", headers=headers
    )
    playthrough_id = response.json()["playthrough_id"]

    stmt = select(Playthrough).where(
        Playthrough.playthrough_id == uuid.UUID(playthrough_id)
    )
    playthrough = (await db_session.execute(stmt)).scalars().first()
    playthrough.turn_count = 15
    await db_session.flush()

    review_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/reviews",
        json={"rating": 5, "comment": "Great!"},
        headers=headers,
    )
    assert review_resp.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_deep_copies_master_mode_resources(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    seeded = await _seed_master_world(async_client, headers, master_scenario_id)

    dup_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/duplicate", headers=headers
    )
    assert dup_resp.status_code == 201
    new_scenario = dup_resp.json()
    assert new_scenario["scenario_id"] != master_scenario_id
    assert new_scenario["status"] == "draft"
    assert new_scenario["creator_id"] == str(dev_user.user_id)

    new_scenario_id = new_scenario["scenario_id"]

    entities_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/entities", headers=headers
    )
    entity_ids = {e["entity_id"] for e in entities_resp.json()["items"]}
    assert len(entity_ids) == 3
    assert seeded["warden_id"] not in entity_ids
    assert seeded["cairn_id"] not in entity_ids
    assert seeded["crypt_id"] not in entity_ids

    facts_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/facts", headers=headers
    )
    facts = facts_resp.json()["items"]
    assert len(facts) == 1
    assert facts[0]["fact_id"] != seeded["fact_id"]
    assert facts[0]["subject_entity_id"] in entity_ids
    assert facts[0]["object_entity_id"] in entity_ids

    conditions_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/conditions", headers=headers
    )
    assert len(conditions_resp.json()["items"]) == 1
    assert conditions_resp.json()["items"][0]["condition_id"] != seeded["condition_id"]

    end_conditions_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/end_conditions", headers=headers
    )
    assert len(end_conditions_resp.json()["items"]) == 1
    assert (
        end_conditions_resp.json()["items"][0]["end_condition_id"]
        != seeded["end_condition_id"]
    )

    invariants_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/invariants", headers=headers
    )
    assert len(invariants_resp.json()["items"]) == 1
    assert invariants_resp.json()["items"][0]["invariant_id"] != seeded["invariant_id"]

    # Verify entity types are deep-copied
    entity_types_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/entity-types", headers=headers
    )
    entity_types = entity_types_resp.json()["items"]
    assert len(entity_types) == 1
    assert entity_types[0]["scenario_entity_type_id"] != seeded["entity_type_id"]
    assert entity_types[0]["type_key"] == "artifact"

    # Verify maps are deep-copied
    maps_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/maps", headers=headers
    )
    maps = maps_resp.json()["items"]
    assert len(maps) == 1
    assert maps[0]["map_id"] != seeded["map_id"]
    assert maps[0]["name"] == "Upper Realm"
    new_map_id = maps[0]["map_id"]

    # Verify pins are deep-copied with remapped map_id and entity_id
    pins_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/maps/{new_map_id}/pins", headers=headers
    )
    pins = pins_resp.json()["items"]
    assert len(pins) == 2
    pin_ids = {p["pin_id"] for p in pins}
    assert seeded["pin1_id"] not in pin_ids
    assert seeded["pin2_id"] not in pin_ids
    assert all(p["entity_id"] in entity_ids for p in pins)
    assert all(p["map_id"] == new_map_id for p in pins)
    start_pins = [p for p in pins if p["is_start_location"]]
    assert len(start_pins) == 1

    # Verify map connections are deep-copied with sorted entity pairs
    conns_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/map-connections", headers=headers
    )
    conns = conns_resp.json()["items"]
    assert len(conns) == 1
    assert conns[0]["connection_id"] != seeded["connection_id"]
    assert conns[0]["label"] == "Stone Bridge"
    assert conns[0]["entity_id_a"] in entity_ids
    assert conns[0]["entity_id_b"] in entity_ids
    assert uuid.UUID(conns[0]["entity_id_a"]) < uuid.UUID(conns[0]["entity_id_b"])

    # Verify minigames are deep-copied
    minigames_resp = await async_client.get(
        f"/v1/scenarios/{new_scenario_id}/minigames", headers=headers
    )
    minigames = minigames_resp.json()["items"]
    assert len(minigames) == 1
    assert minigames[0]["minigame_id"] != seeded["minigame_id"]
    assert minigames[0]["label"] == "Dodge Falling Rocks"
    assert minigames[0]["minigame_type"] == "dodge"

    original_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/entities", headers=headers
    )
    original_entity_ids = {e["entity_id"] for e in original_resp.json()["items"]}
    assert original_entity_ids == {
        seeded["warden_id"],
        seeded["cairn_id"],
        seeded["crypt_id"],
    }


@pytest.mark.asyncio
async def test_duplicate_rejects_non_owner(
    async_client: AsyncClient, dev_user2, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user2.user_id)}
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/duplicate", headers=headers
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_duplicate_copies_content_tags_and_the_age_rating(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    payload = {
        "title": "Tagged Original",
        "mode": "newbie",
        "complexity_tier": "newbie",
        "content_tag": "teen",
        "content_tags": ["cozy-tone", "found-family"],
    }
    original = (
        await async_client.post("/v1/scenarios", json=payload, headers=headers)
    ).json()

    dup_resp = await async_client.post(
        f"/v1/scenarios/{original['scenario_id']}/duplicate", headers=headers
    )

    copy = dup_resp.json()
    assert dup_resp.status_code == 201
    assert copy["content_tags"] == ["cozy-tone", "found-family"]
    assert copy["content_tag"] == "teen"


@pytest.mark.asyncio
async def test_duplicate_copies_mood_music_for_newbie_scenario(
    async_client: AsyncClient, dev_user, db_session: AsyncSession
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    original = (
        await async_client.post(
            "/v1/scenarios",
            json={"title": "Scored", "mode": "newbie", "complexity_tier": "newbie"},
            headers=headers,
        )
    ).json()
    music_repo = ScenarioMusicRepo(db_session)
    source_id = uuid.UUID(original["scenario_id"])
    await music_repo.upsert(source_id, "combat", "upload", "https://x/combat.mp3")
    await music_repo.upsert(
        source_id, "peaceful", "generated", "https://x/calm.mp3", bpm=72
    )

    dup_resp = await async_client.post(
        f"/v1/scenarios/{source_id}/duplicate", headers=headers
    )

    assert dup_resp.status_code == 201
    copied = await music_repo.get_by_scenario(uuid.UUID(dup_resp.json()["scenario_id"]))
    copied_by_mood = {track.mood: track for track in copied}
    assert set(copied_by_mood) == {"combat", "peaceful"}
    assert copied_by_mood["combat"].track_url == "https://x/combat.mp3"
    assert copied_by_mood["peaceful"].source == "generated"
    assert copied_by_mood["peaceful"].bpm == 72


async def _require_player_name(
    async_client: AsyncClient, headers: dict, scenario_id: str
) -> None:
    await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={
            "setup_schema": [
                {"field_key": "player_name", "type": "text", "required": True}
            ]
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_playtest_accepts_setup_values_for_required_fields(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    await _require_player_name(async_client, headers, master_scenario_id)

    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/playtest",
        json={"setup_values": {"player_name": "Ash"}},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["is_playtest"] is True


@pytest.mark.asyncio
async def test_playtest_without_required_setup_values_is_rejected(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    await _require_player_name(async_client, headers, master_scenario_id)

    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/playtest", headers=headers
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_scenario_copies_master_rows_even_when_mode_is_newbie(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    await _seed_master_world(async_client, headers, master_scenario_id)
    switched = await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}", json={"mode": "newbie"}, headers=headers
    )
    assert switched.json()["mode"] == "newbie"

    dup_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/duplicate", headers=headers
    )

    assert dup_resp.status_code == 201
    new_id = dup_resp.json()["scenario_id"]
    assert dup_resp.json()["mode"] == "newbie"
    await async_client.patch(
        f"/v1/scenarios/{new_id}", json={"mode": "master"}, headers=headers
    )
    for path, count in [
        ("conditions", 1),
        ("end_conditions", 1),
        ("invariants", 1),
        ("maps", 1),
        ("minigames", 1),
    ]:
        listed = await async_client.get(
            f"/v1/scenarios/{new_id}/{path}", headers=headers
        )
        assert len(listed.json()["items"]) == count, path


@pytest.mark.asyncio
async def test_duplicate_copies_ui_metadata_on_end_conditions_and_invariants(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    ui_metadata = {"rows": [{"comparison": "drops_to"}], "joiner": "and"}
    base = f"/v1/scenarios/{master_scenario_id}"
    await async_client.post(
        f"{base}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "lose",
            "outcome_title": "Gone",
            "outcome_text": "The light fades.",
            "metadata": ui_metadata,
        },
        headers=headers,
    )
    await async_client.post(
        f"{base}/invariants",
        json={
            "label": "Floor",
            "invariant_expression": {"field": "player.health", "op": ">=", "value": 0},
            "applies_to": "global",
            "narrator_text": "Never below zero.",
            "metadata": ui_metadata,
        },
        headers=headers,
    )

    duplicate = await async_client.post(f"{base}/duplicate", headers=headers)
    new_base = f"/v1/scenarios/{duplicate.json()['scenario_id']}"
    end_conditions = await async_client.get(
        f"{new_base}/end_conditions", headers=headers
    )
    invariants = await async_client.get(f"{new_base}/invariants", headers=headers)

    assert end_conditions.json()["items"][0]["metadata"] == ui_metadata
    assert invariants.json()["items"][0]["metadata"] == ui_metadata


OVERRIDE_STATE_SCHEMA = {
    "lantern_oil": {"type": "number", "initial": 8, "min": 0, "max": 10},
    "has_escaped": {"type": "boolean", "initial": False},
    "time_of_day": {
        "type": "enum",
        "options": ["dawn", "day", "night"],
        "initial": "dawn",
    },
}


@pytest.fixture
async def override_scenario_id(async_client: AsyncClient, dev_user) -> str:
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await async_client.post(
        "/v1/scenarios",
        json={"title": "Lantern Run", "mode": "master", "complexity_tier": "master"},
        headers=headers,
    )
    scenario_id = created.json()["scenario_id"]
    patched = await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"state_schema": OVERRIDE_STATE_SCHEMA},
        headers=headers,
    )
    assert patched.status_code == 200
    return scenario_id


async def _count_playthroughs(db_session: AsyncSession, scenario_id: str) -> int:
    result = await db_session.execute(
        select(Playthrough).where(Playthrough.scenario_id == uuid.UUID(scenario_id))
    )
    return len(result.scalars().all())


async def _playtest_with(
    async_client: AsyncClient, user, scenario_id: str, overrides: dict[str, object]
):
    return await async_client.post(
        f"/v1/scenarios/{scenario_id}/playtest",
        json={"state_overrides": overrides},
        headers={"x-dev-user-id": str(user.user_id)},
    )


@pytest.mark.asyncio
async def test_override_sets_number_value_in_initial_state(
    async_client: AsyncClient, dev_user, override_scenario_id: str
):
    response = await _playtest_with(
        async_client,
        dev_user,
        override_scenario_id,
        {"lantern_oil": 2, "has_escaped": True, "time_of_day": "night"},
    )

    assert response.status_code == 201
    state = response.json()["state"]
    assert state["lantern_oil"] == 2
    assert state["has_escaped"] is True
    assert state["time_of_day"] == "night"


@pytest.mark.asyncio
async def test_playtest_without_overrides_unchanged(
    async_client: AsyncClient, dev_user, override_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    bare = await async_client.post(
        f"/v1/scenarios/{override_scenario_id}/playtest", headers=headers
    )
    empty = await _playtest_with(async_client, dev_user, override_scenario_id, {})

    for response in (bare, empty):
        assert response.status_code == 201
        assert response.json()["state"]["lantern_oil"] == 8
        assert response.json()["state"]["has_escaped"] is False
        assert response.json()["state"]["time_of_day"] == "dawn"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"nonsense": 1},
        {"lantern_oil": 99},
        {"lantern_oil": "plenty"},
        {"has_escaped": "yes"},
        {"time_of_day": "dusk"},
        {"lantern_oil": 3, "time_of_day": "dusk"},
    ],
    ids=[
        "unknown_key",
        "out_of_range",
        "wrong_type",
        "wrong_boolean_type",
        "enum_not_in_options",
        "one_bad_entry",
    ],
)
async def test_invalid_overrides_are_422_and_create_nothing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
    override_scenario_id: str,
    overrides: dict[str, object],
):
    response = await _playtest_with(
        async_client, dev_user, override_scenario_id, overrides
    )

    assert response.status_code == 422
    assert await _count_playthroughs(db_session, override_scenario_id) == 0


@pytest.mark.asyncio
async def test_override_non_owner_404_or_403_creates_nothing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user2,
    override_scenario_id: str,
):
    response = await _playtest_with(
        async_client, dev_user2, override_scenario_id, {"lantern_oil": 2}
    )

    assert response.status_code in (403, 404)
    assert await _count_playthroughs(db_session, override_scenario_id) == 0


@pytest.mark.asyncio
async def test_override_rejected_on_non_playtest_playthrough_create(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
    override_scenario_id: str,
):
    response = await async_client.post(
        "/v1/playthroughs",
        json={
            "scenario_id": override_scenario_id,
            "state_overrides": {"lantern_oil": 2},
        },
        headers={"x-dev-user-id": str(dev_user.user_id)},
    )

    assert response.status_code == 422
    assert await _count_playthroughs(db_session, override_scenario_id) == 0


@pytest.mark.asyncio
async def test_override_is_rejected_for_a_story_with_advanced_mode_off(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
    override_scenario_id: str,
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    await async_client.patch(
        f"/v1/scenarios/{override_scenario_id}",
        json={"mode": "newbie"},
        headers=headers,
    )

    response = await _playtest_with(
        async_client, dev_user, override_scenario_id, {"lantern_oil": 2}
    )

    assert response.status_code == 422
    assert await _count_playthroughs(db_session, override_scenario_id) == 0


@pytest.mark.asyncio
async def test_duplicate_copies_the_strategy_map(async_client: AsyncClient, dev_user):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "strategy_document": StrategyScenario().model_dump(mode="json"),
        },
        headers=headers,
    )
    scenario_id = created.json()["scenario_id"]
    traced_map = json.loads(TRACED_MAP_PATH.read_text())
    await async_client.put(
        f"/v1/scenarios/{scenario_id}/strategy-map", json=traced_map, headers=headers
    )

    duplicate = await async_client.post(
        f"/v1/scenarios/{scenario_id}/duplicate", headers=headers
    )
    copied_map = await async_client.get(
        f"/v1/scenarios/{duplicate.json()['scenario_id']}/strategy-map",
        headers=headers,
    )

    assert duplicate.status_code == 201
    assert copied_map.json() == traced_map
