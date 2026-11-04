"""Integration tests for ConditionRepo against a real test Postgres."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.user import User
from app.repositories.condition_repo import ConditionRepo
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession

BASE_TIME = datetime(2026, 10, 26, tzinfo=timezone.utc)


@pytest.fixture
async def master_scenario(db_session: AsyncSession) -> Scenario:
    creator: User = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )
    scenario = Scenario(
        creator_id=creator.user_id,
        title="Ordered",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


def _condition(scenario_id: uuid.UUID, label: str, offset_seconds: int):
    return ScenarioCondition(
        scenario_id=scenario_id,
        label=label,
        narrator_instruction="",
        created_at=BASE_TIME + timedelta(seconds=offset_seconds),
    )


@pytest.mark.asyncio
async def test_list_by_scenario_returns_authoring_order(
    db_session: AsyncSession, master_scenario: Scenario
):
    repo = ConditionRepo(db_session)
    scenario_id = master_scenario.scenario_id
    # Inserted out of order on purpose: the listing must follow created_at.
    await repo.create_all(
        [
            _condition(scenario_id, "third", 3),
            _condition(scenario_id, "first", 1),
            _condition(scenario_id, "second", 2),
        ]
    )

    listed = await repo.list_by_scenario(scenario_id)

    assert [c.label for c in listed] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_list_by_scenario_breaks_created_at_ties_by_id(
    db_session: AsyncSession, master_scenario: Scenario
):
    repo = ConditionRepo(db_session)
    scenario_id = master_scenario.scenario_id
    tied = [_condition(scenario_id, f"tied-{n}", 0) for n in range(4)]
    await repo.create_all(tied)

    first = [c.condition_id for c in await repo.list_by_scenario(scenario_id)]
    second = [c.condition_id for c in await repo.list_by_scenario(scenario_id)]

    assert first == sorted(first, key=lambda value: str(value))
    assert first == second
