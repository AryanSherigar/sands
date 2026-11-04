"""Seeding against a real test Postgres: round-trip, order, idempotency and a
playtest playthrough created through PlaythroughService."""

import sys
import uuid

import pytest
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.scenario_map import ScenarioMap
from app.db.models.user import User
from app.exceptions.scenario_exceptions import ScenarioAlreadyPublishingError
from app.models.playthrough import PlaythroughCreate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.user_repo import UserRepo
from scripts.reincarnated_aristocrat.builder import build
from scripts.reincarnated_aristocrat.ids import SCENARIO_ID, entity_id
from scripts.reincarnated_aristocrat.persist import persist
from scripts.seed_reincarnated_aristocrat import parse_args, resolve_creator
from scripts.seeding.playtest import create_playtest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

HIDDEN_STATE_ROOTS = ("sheet", "time", "beats", "policies", "intent")
VISIBLE_STATE_KEYS = ("funds", "resources", "control", "army_strength", "standing")
SERVER_ONLY_SNAPSHOT_KEYS = (
    "scenario_conditions",
    "rule_invariants",
    "scenario_minigames",
    "narrator_persona",
)
ENDING_PUBLIC_KEYS = {"outcome_title", "outcome_tag", "outcome_text"}


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _count(session: AsyncSession, model: type) -> int:
    statement = (
        select(func.count()).select_from(model).where(model.scenario_id == SCENARIO_ID)
    )
    return (await session.execute(statement)).scalar_one()


@pytest.mark.asyncio
async def test_persisted_conditions_come_back_in_authoring_order(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)

    stored = await ConditionRepo(db_session).list_by_scenario(SCENARIO_ID)

    assert [row.label for row in stored] == [item.label for item in built.conditions]
    assert stored[0].label == "G01 Turn counter"


@pytest.mark.asyncio
async def test_persisted_scenario_matches_the_build(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)

    scenario = await db_session.get(Scenario, SCENARIO_ID)
    assert scenario is not None
    assert scenario.mode == "master"
    assert scenario.visibility == "private"
    assert scenario.status == "draft"
    assert scenario.is_mature is False
    assert scenario.enabled_tools == ["status_hud"]
    assert scenario.state_schema == built.scenario["state_schema"]
    assert scenario.action_chips == built.scenario["action_chips"]
    assert len(await EntityRepo(db_session).list_by_scenario(SCENARIO_ID)) == 38
    endings = await EndConditionRepo(db_session).list_by_scenario(SCENARIO_ID)
    assert next(ending.outcome_title for ending in endings) == "The Household Turns"


@pytest.mark.asyncio
async def test_the_eight_maps_are_written_with_one_start_pin(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)

    assert await _count(db_session, ScenarioMap) == 8
    assert await _count(db_session, MapPin) == 28
    expected = sum(len(item.connections) for item in built.maps)
    assert await _count(db_session, MapConnection) == expected
    starts = (
        (await db_session.execute(select(MapPin).where(MapPin.is_start_location)))
        .scalars()
        .all()
    )
    assert [pin.entity_id for pin in starts] == [entity_id("ars_room")]


@pytest.mark.asyncio
async def test_reseeding_replaces_in_place_without_duplicates(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    await persist(db_session, build(), creator.user_id)

    stored = await ConditionRepo(db_session).list_by_scenario(SCENARIO_ID)

    assert len(stored) == len(build().conditions)
    assert len({row.label for row in stored}) == len(stored)
    assert await _count(db_session, MapPin) == 28


@pytest.mark.asyncio
async def test_seeding_is_refused_while_the_scenario_is_publishing(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    scenario = await db_session.get(Scenario, SCENARIO_ID)
    scenario.status = "publishing"
    await db_session.flush()

    with pytest.raises(ScenarioAlreadyPublishingError):
        await persist(db_session, build(), creator.user_id)


@pytest.mark.asyncio
async def test_a_playtest_playthrough_starts_from_the_seeded_initial_state(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values={})

    response = await create_playtest(db_session, creator.user_id, data)

    row = await db_session.get(Playthrough, response.playthrough_id)
    assert row is not None
    assert row.scenario_snapshot["visibility"] == "private"
    assert row.state["player"]["age"] == 6
    assert row.state["funds"] == 60
    assert row.state["sheet"]["competence"] == 40
    assert row.state["intent"]["train_who"] == ""
    assert row.state["current_location_id"] == str(entity_id("ars_room"))
    ritsu = row.state["entities"][str(entity_id("ritsu"))]
    assert ritsu["leadership"] == 30
    assert ritsu["is_recruited"] is False
    assert ritsu["loyalty"] == 40


@pytest.mark.asyncio
async def test_the_client_never_sees_the_hidden_sheet_clock_or_intents(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values={})

    response = await create_playtest(db_session, creator.user_id, data)

    assert "visibility" not in response.scenario_snapshot
    assert not set(HIDDEN_STATE_ROOTS) & set(response.state)
    assert all(key in response.state for key in VISIBLE_STATE_KEYS)
    assert not set(SERVER_ONLY_SNAPSHOT_KEYS) & set(response.scenario_snapshot)
    schema_text = str(response.scenario_snapshot["state_schema"])
    assert "competence" not in schema_text
    assert "clock_days" not in schema_text
    start = response.state["current_location_id"]
    assert response.state["discovered_location_ids"] == [start]


@pytest.mark.asyncio
async def test_secret_endings_are_withheld_and_the_rest_are_trimmed(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values={})

    response = await create_playtest(db_session, creator.user_id, data)

    endings = response.scenario_snapshot["end_conditions"]
    titles = [ending["outcome_title"] for ending in endings]
    assert "The Lord Everyone Obeys" not in titles
    assert len(titles) == 7
    assert all(set(ending) == ENDING_PUBLIC_KEYS for ending in endings)


@pytest.mark.asyncio
async def test_character_attributes_and_caps_reach_the_client_known_leak(
    db_session: AsyncSession, creator: User
):
    """Characterisation of ADR-17's open follow-up: entity attributes, including
    the hidden caps, are in the client snapshot. Accepted for a private test."""
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values={})

    response = await create_playtest(db_session, creator.user_id, data)

    ritsu = next(
        entity
        for entity in response.scenario_snapshot["entities"]
        if entity["canonical_name"] == "Ritsu Muses"
    )
    assert ritsu["attributes_schema"]["leadership"]["max"] == 99


def _parse(argv: list[str]):
    previous = sys.argv
    sys.argv = ["seed", *argv]
    try:
        return parse_args()
    finally:
        sys.argv = previous


def test_a_creator_id_and_a_creator_name_cannot_be_combined():
    with pytest.raises(SystemExit):
        _parse(["--creator-id", str(uuid.uuid4()), "--creator-name", "dambhare"])


def test_a_creator_can_be_named_by_display_name():
    assert _parse(["--creator-name", "dambhare"]).creator_name == "dambhare"


@pytest.mark.asyncio
async def test_resolving_a_creator_without_any_name_or_id_fails():
    with pytest.raises(RuntimeError, match="no default"):
        await resolve_creator(None, None)
