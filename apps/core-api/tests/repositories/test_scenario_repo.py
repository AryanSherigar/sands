"""Integration tests for ScenarioRepo against a real test Postgres instance."""

import uuid

import pytest
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.models.scenario import ScenarioResponse
from app.repositories.scenario_repo import ScenarioRepo
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(
        user_id=uuid.uuid4(),
        display_name="Tester",
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def scenario(db_session: AsyncSession, user: User) -> Scenario:
    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=user.user_id,
        title="Test Scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="both",
        status="published",
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.mark.asyncio
async def test_create_or_update_review_updates_scenario_rating_avg(
    db_session: AsyncSession, user: User, scenario: Scenario
) -> None:
    repo = ScenarioRepo(db_session)

    await repo.create_or_update_review(user.user_id, scenario.scenario_id, 4, "Good")
    review, display_name = await repo.create_or_update_review(
        user.user_id, scenario.scenario_id, 2, "Actually mediocre"
    )

    assert review.rating == 2
    assert review.comment == "Actually mediocre"
    assert display_name == "Tester"
    updated = await repo.get_by_id(scenario.scenario_id)
    assert float(updated.rating_avg) == 2.0


@pytest.mark.asyncio
async def test_create_or_update_review_locks_scenario_row(
    db_session: AsyncSession, user: User, scenario: Scenario, monkeypatch
) -> None:
    """Regression test for MED-04: the scenario row must be fetched via the
    locked get_by_id_for_update path, not a raw unlocked select."""
    repo = ScenarioRepo(db_session)
    calls: list[uuid.UUID] = []
    original = repo.get_by_id_for_update

    async def _spy(scenario_id: uuid.UUID) -> Scenario | None:
        calls.append(scenario_id)
        return await original(scenario_id)

    monkeypatch.setattr(repo, "get_by_id_for_update", _spy)

    await repo.create_or_update_review(user.user_id, scenario.scenario_id, 5, None)

    assert calls == [scenario.scenario_id]


@pytest.mark.asyncio
async def test_new_scenario_has_no_enabled_tools(
    db_session: AsyncSession, scenario: Scenario
) -> None:
    await db_session.refresh(scenario)

    assert scenario.enabled_tools == []


@pytest.mark.asyncio
async def test_scenario_response_exposes_enabled_tools(
    db_session: AsyncSession, scenario: Scenario
) -> None:
    scenario.enabled_tools = ["status_hud"]
    await db_session.flush()
    await db_session.refresh(scenario)

    response = ScenarioResponse.model_validate(scenario)

    assert response.enabled_tools == ["status_hud"]
