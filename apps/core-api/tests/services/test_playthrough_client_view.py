"""PlaythroughResponse never carries hidden state or server-only snapshot keys."""

import uuid

import pytest
from app.db.models.entity import Entity
from app.models.playthrough import PlaythroughCreate
from app.repositories.playthrough_repo import PlaythroughRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_playthrough_initial_state import _master_scenario
from tests.services.test_tool_snapshot import _make_service

SCHEMA = {
    "clock": {"type": "number", "initial": 0},
    "dread": {"type": "number", "initial": 7, "hidden": True},
}


@pytest.mark.asyncio
async def test_character_avatars_are_pinned_but_not_disclosed_without_scene_presence(
    db_session,
):
    user_id, scenario = await _master_scenario(db_session, SCHEMA)
    character = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="character",
        canonical_name="Asha",
        avatar_url="https://assets.example/asha.mavatar",
    )
    db_session.add(character)
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    stored = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    assert stored.scenario_snapshot["character_avatar_assets"] == {
        str(character.entity_id): "https://assets.example/asha.mavatar"
    }
    assert "character_avatar_assets" not in created.scenario_snapshot
    assert all(
        "avatar_url" not in entity for entity in created.scenario_snapshot["entities"]
    )
    character.avatar_url = "https://assets.example/changed.mavatar"
    await db_session.flush()
    assert (
        stored.scenario_snapshot["character_avatar_assets"][str(character.entity_id)]
        == "https://assets.example/asha.mavatar"
    )


@pytest.mark.asyncio
async def test_slice_of_life_projects_only_explicit_present_portraits(db_session):
    user_id, scenario = await _master_scenario(db_session, {})
    character = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="character",
        canonical_name="Asha",
        avatar_url="https://assets.example/asha.mavatar",
    )
    db_session.add(character)
    await db_session.flush()
    scenario.genre_tags = ["Slice of Life"]
    scenario.state_schema = {
        "scene_character_ids": {
            "type": "list",
            "item_type": "entity_ref",
            "initial": [str(character.entity_id)],
        }
    }
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    assert created.scenario_snapshot["scene_portraits"] == [
        {
            "entity_id": str(character.entity_id),
            "name": "Asha",
            "avatar_url": character.avatar_url,
        }
    ]
    row = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    row.state = {**row.state, "scene_character_ids": []}
    await db_session.flush()
    fetched = await service.get_playthrough(row.playthrough_id, user_id)
    assert "scene_portraits" not in fetched.scenario_snapshot


@pytest.mark.asyncio
async def test_simple_story_pins_explicit_opening_portraits(db_session):
    user_id, scenario = await _master_scenario(db_session, {})
    scenario.mode = "newbie"
    scenario.genre_tags = ["Slice of Life"]
    character = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="character",
        canonical_name="Asha",
        avatar_url="https://assets.example/asha.mavatar",
    )
    db_session.add(character)
    await db_session.flush()
    scenario.rules = {
        "portrait_opening_ids": [str(character.entity_id)],
        "portrait_schedule": [{"turn": 1, "character_ids": []}],
    }
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    assert created.state["scene_character_ids"] == [str(character.entity_id)]
    assert created.scenario_snapshot["scene_portraits"][0]["name"] == "Asha"
    row = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    row.turn_count = 1
    await db_session.flush()
    after = await service.get_playthrough(row.playthrough_id, user_id)
    assert "scene_portraits" not in after.scenario_snapshot


@pytest.mark.asyncio
async def test_combat_configuration_is_pinned_but_not_sent_to_player(db_session):
    user_id, scenario = await _master_scenario(db_session, SCHEMA)
    config = {"encounters": [{"encounter_id": "ambush", "secret": "hidden"}]}
    scenario.rules = {"fantasy_combat": config}
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    stored = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    assert stored.scenario_snapshot["fantasy_combat"] == config
    assert "fantasy_combat" not in created.scenario_snapshot
    assert created.scenario_snapshot["combat_enabled"] is True


@pytest.mark.asyncio
async def test_combat_events_do_not_change_story_turn_count_or_history(db_session):
    from app.db.models.turn_log import TurnLog

    service, user_id, created = await _create(db_session)
    row = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    row.turn_count = 2
    row.state = {**row.state, "_combat": {"status": "opponent_defeated"}}
    db_session.add_all(
        [
            TurnLog(
                playthrough_id=row.playthrough_id,
                turn_number=1,
                action_text="Look",
                narration_text="A road.",
                tool_calls=[],
            ),
            TurnLog(
                playthrough_id=row.playthrough_id,
                turn_number=2,
                action_text="Combat",
                narration_text="",
                tool_calls=[{"tool_name": "_combat_action"}],
            ),
        ]
    )
    await db_session.commit()
    fetched = await service.get_playthrough(row.playthrough_id, user_id)
    turns = await service.list_turns(row.playthrough_id, user_id, None, 1, 20, None)
    assert fetched.turn_count == 2 and fetched.narrative_turn_count == 1
    assert turns.total_count == 1 and turns.items[0].narration_text == "A road."


@pytest.mark.asyncio
async def test_creator_combat_health_is_initialized_and_snapshot_is_pinned(db_session):
    schema = {
        "ready": {"type": "boolean", "initial": True},
        "player": {
            "type": "object",
            "fields": {
                "health": {"type": "number", "initial": 12, "min": 0, "max": 20}
            },
        },
    }
    user_id, scenario = await _master_scenario(db_session, schema)
    stats = {
        "max_health": 20,
        "health": 12,
        "attack": 6,
        "armor": 2,
        "speed": 4,
        "accuracy": 75,
        "luck": 10,
    }
    encounter = {
        "encounter_id": "example",
        "title": "Example",
        "start_condition": {"field": "ready", "op": "==", "value": True},
        "player": {"actor_id": "player", "side": "player", **stats},
        "opponent": {"actor_id": "opponent-example", "side": "opponent", **stats},
        "outcomes": [{"id": "recovery", "kind": "recover", "health": 4}],
        "fallback_outcome_id": "recovery",
    }
    scenario.rules = {"fantasy_combat": {"encounters": [encounter]}}
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    stored = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)
    assert created.state["player"]["health"] == 12
    assert stored.scenario_snapshot["fantasy_combat"]["encounters"] == [encounter]


@pytest.mark.asyncio
async def test_new_advanced_snapshot_pins_fantasy_genre_and_safe_config(
    db_session: AsyncSession,
):
    user_id, scenario = await _master_scenario(db_session, SCHEMA)
    scenario.genre_tags = ["High Fantasy"]
    locations = {
        key: str(uuid.uuid4())
        for key in ("inn", "quest_giver", "recovery", "cremation")
    }
    item = str(uuid.uuid4())
    for location in locations.values():
        db_session.add(
            Entity(
                entity_id=uuid.UUID(location),
                scenario_id=scenario.scenario_id,
                entity_type="location",
                canonical_name=location,
            )
        )
    db_session.add(
        Entity(
            entity_id=uuid.UUID(item),
            scenario_id=scenario.scenario_id,
            entity_type="item",
            canonical_name="Test item",
        )
    )
    classes = (
        "disgraced_knight",
        "rogue_apprentice",
        "fugitive_smuggler",
        "last_priest",
    )
    scenario.setup_schema = [
        {
            "key": "outlander_class",
            "type": "single_select",
            "required": True,
            "options": list(classes),
        }
    ]
    scenario.rules = {
        "fantasy_mechanics": {
            "version": 1,
            "profile": "zegaris",
            "rest_cost": 5,
            "locations": locations,
            "corpse_item_id": item,
            "class_loadouts": {key: [item] for key in classes},
            "secret": "private",
        }
    }
    await db_session.flush()
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(
            scenario_id=scenario.scenario_id,
            setup_values={"outlander_class": "disgraced_knight"},
        ),
    )
    assert created.scenario_snapshot["genre_tags"] == ["High Fantasy"]
    assert "secret" not in created.scenario_snapshot["fantasy_mechanics"]
    assert created.state["player"]["coins"] == 10
    assert created.state["player"]["inventory"] == [item]
    assert created.state["quests"]["retrieval"]["stage"] == "offered"


async def _create(db_session: AsyncSession):
    user_id, scenario = await _master_scenario(db_session, SCHEMA)
    service = _make_service(db_session)
    created = await service.create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    return service, user_id, created


@pytest.mark.asyncio
async def test_create_response_hides_hidden_state_but_database_keeps_it(
    db_session: AsyncSession,
):
    _, _, created = await _create(db_session)

    stored = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)

    assert "dread" not in created.state
    assert created.state["clock"] == 0
    assert stored.state["dread"] == 7


@pytest.mark.asyncio
async def test_get_response_hides_hidden_state_and_server_only_snapshot_keys(
    db_session: AsyncSession,
):
    service, user_id, created = await _create(db_session)

    fetched = await service.get_playthrough(created.playthrough_id, user_id)

    assert "dread" not in fetched.state
    assert "dread" not in fetched.scenario_snapshot["state_schema"]
    for private_key in ("scenario_conditions", "rule_invariants", "scenario_minigames"):
        assert private_key not in fetched.scenario_snapshot
    assert fetched.scenario_snapshot["enabled_tools"] == []


@pytest.mark.asyncio
async def test_stored_snapshot_still_carries_everything_for_trs(
    db_session: AsyncSession,
):
    _, _, created = await _create(db_session)

    stored = await PlaythroughRepo(db_session).get_by_id(created.playthrough_id)

    assert "scenario_conditions" in stored.scenario_snapshot
    assert "dread" in stored.scenario_snapshot["state_schema"]
