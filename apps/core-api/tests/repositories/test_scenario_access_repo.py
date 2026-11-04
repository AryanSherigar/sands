"""The private-scenario allowlist, and the public counts that must ignore private ones."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.scenario import Scenario
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


async def make_user(db_session: AsyncSession, name: str):
    return await UserRepo(db_session).create(f"uid-{uuid.uuid4()}", name)


async def make_scenario(
    db_session: AsyncSession, creator, title: str, visibility: str
) -> Scenario:
    scenario = Scenario(
        creator_id=creator.user_id,
        title=title,
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
        visibility=visibility,
        narrator_persona="A narrator.",
        world_data={"lore": "Lore."},
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await make_user(db_session, "Creator")


@pytest.fixture
async def guest(db_session: AsyncSession):
    return await make_user(db_session, "Guest")


async def test_an_added_user_is_allowed_and_a_stranger_is_not(
    db_session, creator, guest
):
    scenario = await make_scenario(db_session, creator, "Tale", "private")
    repo = ScenarioAccessRepo(db_session)
    await repo.add(scenario.scenario_id, guest.user_id)

    assert await repo.is_allowed(scenario.scenario_id, guest.user_id) is True
    assert await repo.is_allowed(scenario.scenario_id, creator.user_id) is False
    assert await repo.list_user_ids(scenario.scenario_id) == [guest.user_id]


async def test_adding_twice_keeps_one_row(db_session, creator, guest):
    scenario = await make_scenario(db_session, creator, "Tale", "private")
    repo = ScenarioAccessRepo(db_session)
    await repo.add(scenario.scenario_id, guest.user_id)
    await repo.add(scenario.scenario_id, guest.user_id)

    assert await repo.list_user_ids(scenario.scenario_id) == [guest.user_id]


async def test_removing_a_user_revokes_access(db_session, creator, guest):
    scenario = await make_scenario(db_session, creator, "Tale", "private")
    repo = ScenarioAccessRepo(db_session)
    await repo.add(scenario.scenario_id, guest.user_id)
    await repo.remove(scenario.scenario_id, guest.user_id)

    assert await repo.is_allowed(scenario.scenario_id, guest.user_id) is False


async def test_the_allowlist_goes_with_its_scenario(db_session, creator, guest):
    scenario = await make_scenario(db_session, creator, "Tale", "private")
    repo = ScenarioAccessRepo(db_session)
    await repo.add(scenario.scenario_id, guest.user_id)
    await db_session.execute(
        delete(Scenario).where(Scenario.scenario_id == scenario.scenario_id)
    )

    assert await repo.list_user_ids(scenario.scenario_id) == []


async def test_a_creators_public_counts_ignore_private_scenarios(db_session, creator):
    public = await make_scenario(db_session, creator, "Open", "public")
    await make_scenario(db_session, creator, "Hidden", "private")
    await make_scenario(db_session, creator, "Another open", "public")

    others = await ScenarioRepo(db_session).count_other_published_by_creator(
        creator.user_id, public.scenario_id
    )
    authored, _ = await UserRepo(db_session).get_creator_stats(creator.user_id)

    assert others == 1
    assert authored == 2


async def test_the_visibility_lookup_returns_none_for_an_unknown_scenario(db_session):
    assert await ScenarioRepo(db_session).get_visibility(uuid.uuid4()) is None
