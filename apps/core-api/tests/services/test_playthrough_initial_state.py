"""create_playthrough seeds Playthrough.state from schema and entity initials."""

import uuid

import pytest
from app.db.models.entity import Entity
from app.db.models.scenario import Scenario
from app.exceptions.playthrough_exceptions import InvalidSchemaInitialError
from app.models.playthrough import PlaythroughCreate
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_tool_snapshot import _make_service


async def _master_scenario(db_session: AsyncSession, state_schema: dict[str, object]):
    user = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev User"
    )
    scenario = Scenario(
        creator_id=user.user_id,
        title="Night Desk",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        state_schema=state_schema,
    )
    db_session.add(scenario)
    await db_session.flush()
    return user.user_id, scenario


async def _start(db_session: AsyncSession, user_id, scenario):
    return await _make_service(db_session).create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )


@pytest.mark.asyncio
async def test_new_playthrough_state_has_schema_initials(db_session: AsyncSession):
    user_id, scenario = await _master_scenario(
        db_session,
        {
            "sanity": {"type": "number", "initial": 85},
            "player": {
                "type": "object",
                "fields": {"health": {"type": "number", "initial": 100}},
            },
        },
    )

    result = await _start(db_session, user_id, scenario)

    assert result.state["sanity"] == 85
    assert result.state["player"] == {"health": 100}
    assert result.state["setup"] == {}
    assert result.state["narrative"] == {"opening_prompt": None}


@pytest.mark.asyncio
async def test_system_keys_win_over_schema_initials(db_session: AsyncSession):
    user_id, scenario = await _master_scenario(
        db_session, {"narrative": {"type": "number", "initial": 5}}
    )

    result = await _start(db_session, user_id, scenario)

    assert result.state["narrative"] == {"opening_prompt": None}


@pytest.mark.asyncio
async def test_entity_attribute_initials_are_seeded_per_entity(
    db_session: AsyncSession,
):
    user_id, scenario = await _master_scenario(db_session, {})
    entity = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="character",
        canonical_name="Mr. Hale",
        attributes_schema={"trust": {"type": "number", "initial": 3}},
    )
    db_session.add(entity)
    await db_session.flush()

    result = await _start(db_session, user_id, scenario)

    assert result.state["entities"] == {str(entity.entity_id): {"trust": 3}}


@pytest.mark.asyncio
async def test_initials_never_enter_the_snapshot_state_schema_values(
    db_session: AsyncSession,
):
    schema = {"sanity": {"type": "number", "initial": 85}}
    user_id, scenario = await _master_scenario(db_session, schema)

    result = await _start(db_session, user_id, scenario)

    assert result.scenario_snapshot["state_schema"] == schema
    assert "sanity" not in result.scenario_snapshot


@pytest.mark.asyncio
async def test_invalid_initial_fails_creation_with_clear_error(
    db_session: AsyncSession,
):
    user_id, scenario = await _master_scenario(
        db_session, {"sanity": {"type": "number", "initial": "lots"}}
    )

    with pytest.raises(InvalidSchemaInitialError):
        await _start(db_session, user_id, scenario)


@pytest.mark.asyncio
async def test_opening_scene_is_rendered_into_narrative_with_player_name(
    db_session: AsyncSession,
):
    user_id, scenario = await _master_scenario(db_session, {})
    scenario.opening_scene = "Good evening, {player_name}. Floor 9 is yours."
    scenario.setup_schema = [
        {"key": "character_name", "type": "text", "is_character_name": True}
    ]
    player = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="character",
        canonical_name="Clerk",
        is_player=True,
    )
    db_session.add(player)
    await db_session.flush()

    result = await _make_service(db_session).create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(
            scenario_id=scenario.scenario_id,
            setup_values={"character_name": "Mara"},
        ),
    )

    assert (
        result.state["narrative"]["opening_prompt"]
        == "Good evening, Mara. Floor 9 is yours."
    )


@pytest.mark.asyncio
async def test_opening_scene_without_a_chosen_name_uses_adventurer(
    db_session: AsyncSession,
):
    user_id, scenario = await _master_scenario(db_session, {})
    scenario.opening_scene = "Welcome, {player_name}."
    await db_session.flush()

    result = await _start(db_session, user_id, scenario)

    assert result.state["narrative"]["opening_prompt"] == "Welcome, Adventurer."


@pytest.mark.asyncio
async def test_missing_opening_scene_leaves_prompt_none(db_session: AsyncSession):
    user_id, scenario = await _master_scenario(db_session, {})

    result = await _start(db_session, user_id, scenario)

    assert result.state["narrative"]["opening_prompt"] is None
