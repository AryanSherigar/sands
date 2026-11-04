"""Seeding against a real test Postgres: round-trip, order, idempotency and a
playtest playthrough created through PlaythroughService."""

import uuid

import pytest
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_rule_check import ScenarioRuleCheck
from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from app.db.models.user import User
from app.exceptions.scenario_exceptions import ScenarioAlreadyPublishingError
from app.models.playthrough import PlaythroughCreate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.user_repo import UserRepo
from scripts.night_desk.builder import build
from scripts.night_desk.ids import SCENARIO_ID
from scripts.night_desk.persist import persist
from scripts.night_desk.playtest import create_playtest
from scripts.night_desk.validation import pinned_schema
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

PLAYER_NAME = "Alex"
HIDDEN_STATE_ROOTS = ("seed", "count", "fragments", "flags", "check")
SERVER_ONLY_SNAPSHOT_KEYS = (
    "scenario_conditions",
    "rule_invariants",
    "scenario_minigames",
    "narrator_persona",
    "rule_checks",
    "sheet_rules",
)
SECRET_ENDINGS = ()
SEED_PATH_NEEDLES = ("seed", "false_rule", "regime", "fragments", "rule_status")


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
    assert stored[0].is_one_shot is True
    assert [m["path"] for m in stored[4].state_mutations] == [
        "rule_status.r6",
        "tension_tier",
    ]


@pytest.mark.asyncio
async def test_persisted_scenario_matches_the_build(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)

    scenario = await db_session.get(Scenario, SCENARIO_ID)
    assert scenario is not None
    assert scenario.mode == "master"
    assert scenario.status == "draft"
    assert scenario.is_mature is True
    assert scenario.enabled_tools == built.scenario["enabled_tools"]
    assert scenario.state_schema == built.scenario["state_schema"]
    assert scenario.rules == {}
    assert len(await EntityRepo(db_session).list_by_scenario(SCENARIO_ID)) == 19
    assert len(await FactRepo(db_session).list_by_scenario(SCENARIO_ID)) == 3
    endings = await EndConditionRepo(db_session).list_by_scenario(SCENARIO_ID)
    assert next(ending.outcome_title for ending in endings) == "Counted"
    minigames = await MinigameRepo(db_session).list_by_scenario(SCENARIO_ID)
    assert [row.minigame_type for row in minigames] == ["rhythm_composure"]


@pytest.mark.asyncio
async def test_tool_rows_and_the_map_are_written(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)

    assert await _count(db_session, ScenarioRuleCheck) == 10
    assert await _count(db_session, ScenarioSheetRule) == 8
    assert await _count(db_session, ScenarioMap) == 1
    assert await _count(db_session, MapPin) == 9
    assert await _count(db_session, MapConnection) == 8
    start_pins = (
        (await db_session.execute(select(MapPin).where(MapPin.is_start_location)))
        .scalars()
        .all()
    )
    assert len(start_pins) == 1


@pytest.mark.asyncio
async def test_reseeding_replaces_in_place_without_duplicates(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    await persist(db_session, build(), creator.user_id)

    stored = await ConditionRepo(db_session).list_by_scenario(SCENARIO_ID)

    assert len(stored) == len(build().conditions)
    assert len({row.label for row in stored}) == len(stored)
    assert await _count(db_session, ScenarioRuleCheck) == 10
    assert await _count(db_session, MapPin) == 9


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
async def test_a_playtest_playthrough_can_be_created_from_the_seed(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)
    data = PlaythroughCreate(
        scenario_id=SCENARIO_ID, setup_values={"character_name": PLAYER_NAME}
    )

    response = await create_playtest(db_session, creator.user_id, data)

    row = await db_session.get(Playthrough, response.playthrough_id)
    assert row is not None
    snapshot = row.scenario_snapshot
    assert snapshot["enabled_tools"] == built.scenario["enabled_tools"]
    assert len(snapshot["rule_checks"]) == 10
    assert snapshot["state_schema"] == pinned_schema(built)
    _assert_initial_state(row.state)
    _assert_client_view(response)


def _assert_initial_state(state: dict[str, object]) -> None:
    assert state["shift_minutes"] == 0
    assert state["sanity"] == 85
    assert state["seed"]["false_rule"] in {"r4", "r6"}
    assert all(root in state for root in HIDDEN_STATE_ROOTS)
    assert state["rule_status"]["r1"] == "intact"
    assert state["rule_status"]["r6"] == "unrevealed"
    assert state["current_location_id"]
    assert PLAYER_NAME in str(state["narrative"]["opening_prompt"])


def _assert_client_view(response) -> None:
    start_location = response.state["current_location_id"]
    assert response.state["discovered_location_ids"] == [start_location]
    assert any(
        pin["entity_id"] == str(start_location)
        for pin in response.scenario_snapshot["map_pins"]
    )
    assert "seed" not in response.state
    assert "rule_status" not in response.state
    assert not set(SERVER_ONLY_SNAPSHOT_KEYS) & set(response.scenario_snapshot)
    assert response.scenario_snapshot["enabled_tools"]
    endings = response.scenario_snapshot["end_conditions"]
    assert [
        e["outcome_title"] for e in endings if e["outcome_title"] in SECRET_ENDINGS
    ] == []
    assert all(
        set(e) == {"outcome_title", "outcome_tag", "outcome_text"} for e in endings
    )
    schema_text = str(response.scenario_snapshot["state_schema"])
    assert not any(needle in schema_text for needle in SEED_PATH_NEEDLES)
    assert [rule.key for rule in response.rule_sheet] == ["r1", "r2", "r3", "r4"]


@pytest.mark.asyncio
async def test_the_snapshot_carries_movement_aliases_and_narrator_lines(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(
        scenario_id=SCENARIO_ID, setup_values={"character_name": PLAYER_NAME}
    )

    response = await create_playtest(db_session, creator.user_id, data)

    entities = {e["canonical_name"]: e for e in response.scenario_snapshot["entities"]}
    approach = entities["Outside Cabin 14"]
    cabin = entities["Cabin 14"]
    assert "Cabin 14" in approach["aliases"] and "Cabin 14" in cabin["aliases"]
    assert approach["attributes_schema"]["movement_class"]["initial"] == "approach"
    assert cabin["attributes_schema"]["movement_class"]["initial"] == "interior"
    world_data = response.scenario_snapshot["world_data"]
    assert world_data["escalation_reply"] == "Acknowledged."
    assert world_data["fallback_narration"]
