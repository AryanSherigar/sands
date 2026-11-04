"""Private scenarios through the scenario service: Studio list, duplicate, access."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_access import ScenarioAccessChecker
from app.services.scenario_service import ScenarioService
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
def service(db_session: AsyncSession) -> ScenarioService:
    return ScenarioService(ScenarioRepo(db_session))


async def test_the_studio_list_includes_private_scenarios(db_session, service, creator):
    await make_scenario(db_session, creator, "Open", "public")
    await make_scenario(db_session, creator, "Hidden", "private")

    result = await service.list_my_scenarios(creator.user_id, None, None, 20, 0)

    assert sorted(item.title for item in result.items) == ["Hidden", "Open"]


async def test_the_studio_list_of_another_user_never_includes_them(
    db_session, service, creator
):
    other = await make_user(db_session, "Other")
    await make_scenario(db_session, creator, "Hidden", "private")

    result = await service.list_my_scenarios(other.user_id, None, None, 20, 0)

    assert result.items == []


async def test_a_duplicate_of_a_private_scenario_stays_private(
    db_session, service, creator
):
    source = await make_scenario(db_session, creator, "Hidden", "private")

    copy = await service.duplicate_scenario(source.scenario_id, creator.user_id)

    assert copy.visibility == "private"
    assert copy.status == "draft"


async def test_a_duplicate_of_a_public_scenario_stays_public(
    db_session, service, creator
):
    source = await make_scenario(db_session, creator, "Open", "public")

    copy = await service.duplicate_scenario(source.scenario_id, creator.user_id)

    assert copy.visibility == "public"


async def test_the_checker_allows_the_creator_and_the_allowlist_only(
    db_session, creator
):
    guest = await make_user(db_session, "Guest")
    stranger = await make_user(db_session, "Stranger")
    scenario = await make_scenario(db_session, creator, "Hidden", "private")
    repo = ScenarioAccessRepo(db_session)
    await repo.add(scenario.scenario_id, guest.user_id)
    checker = ScenarioAccessChecker(repo)

    assert await checker.can_open(scenario, creator.user_id) is True
    assert await checker.can_open(scenario, guest.user_id) is True
    assert await checker.can_open(scenario, stranger.user_id) is False
    assert await checker.can_open(scenario, None) is False
    with pytest.raises(ScenarioNotFoundError):
        await checker.ensure_can_open(scenario, stranger.user_id)


async def test_the_checker_lets_everyone_open_a_public_scenario(db_session, creator):
    scenario = await make_scenario(db_session, creator, "Open", "public")
    checker = ScenarioAccessChecker(ScenarioAccessRepo(db_session))

    assert await checker.can_open(scenario, None) is True
