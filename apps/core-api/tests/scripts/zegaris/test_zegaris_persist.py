"""Seeding against a real test Postgres: round-trip, idempotency, and one
playtest playthrough per outlander class created through PlaythroughService."""

import uuid

import pytest
from app.db.models.map_pin import MapPin
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.models.playthrough import PlaythroughCreate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.user_repo import UserRepo
from scripts.seeding.playtest import create_playtest
from scripts.zegaris.builder import build
from scripts.zegaris.ids import SCENARIO_ID, entity_id, entity_ref
from scripts.zegaris.mechanics import CLASS_LOADOUTS
from scripts.zegaris.persist import persist
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

HIDDEN_STATE_ROOTS = ("world", "intent")
SERVER_ONLY_SNAPSHOT_KEYS = ("scenario_conditions", "narrator_persona")


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


def _setup(class_key: str) -> dict[str, object]:
    return {"character_name": "Alex", "outlander_class": class_key}


@pytest.mark.asyncio
async def test_persisted_scenario_matches_the_build(
    db_session: AsyncSession, creator: User
):
    built = build()
    await persist(db_session, built, creator.user_id)

    scenario = await db_session.get(Scenario, SCENARIO_ID)
    stored = await ConditionRepo(db_session).list_by_scenario(SCENARIO_ID)
    assert scenario is not None
    assert scenario.status == "draft"
    assert scenario.visibility == "private"
    assert scenario.genre_tags[0] == "High Fantasy"
    assert [row.label for row in stored] == [item.label for item in built.conditions]


@pytest.mark.asyncio
async def test_reseeding_replaces_in_place_without_duplicates(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    await persist(db_session, build(), creator.user_id)

    pins = (
        select(func.count())
        .select_from(MapPin)
        .where(MapPin.scenario_id == SCENARIO_ID)
    )
    assert (await db_session.execute(pins)).scalar_one() == 15


@pytest.mark.asyncio
@pytest.mark.parametrize("class_key", list(CLASS_LOADOUTS))
async def test_each_class_starts_with_its_gear_coins_and_energy(
    db_session: AsyncSession, creator: User, class_key: str
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values=_setup(class_key))

    response = await create_playtest(db_session, creator.user_id, data)

    row = await db_session.get(Playthrough, response.playthrough_id)
    assert row is not None
    assert row.state["player"]["coins"] == 10
    assert row.state["player"]["energy"] == 70
    assert row.state["player"]["inventory"] == [
        entity_ref(slug) for slug in CLASS_LOADOUTS[class_key]
    ]
    assert row.state["quests"]["retrieval"]["stage"] == "offered"
    assert row.state["world"]["tithe"] == "offered"
    assert row.state["current_location_id"] == str(entity_id("owls_respite"))


@pytest.mark.asyncio
async def test_the_client_never_sees_the_tithe_or_server_only_rules(
    db_session: AsyncSession, creator: User
):
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(
        scenario_id=SCENARIO_ID, setup_values=_setup("last_priest")
    )

    response = await create_playtest(db_session, creator.user_id, data)

    assert not set(HIDDEN_STATE_ROOTS) & set(response.state)
    assert not set(SERVER_ONLY_SNAPSHOT_KEYS) & set(response.scenario_snapshot)
    assert response.scenario_snapshot["combat_enabled"] is True
    text = str(response.scenario_snapshot).lower()
    assert "aftermath" not in text
    assert "twins" not in text
    assert "children" not in text
