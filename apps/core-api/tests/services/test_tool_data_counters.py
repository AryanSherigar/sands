"""Leftover-data counters per tool, against the real test Postgres."""

import uuid

import pytest
from app.db.models.scenario_condition import ScenarioCondition
from app.models.scenario import ScenarioCreate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_service import ScenarioService
from app.tools.data_counters import count_tool_rows
from sqlalchemy.ext.asyncio import AsyncSession

HINTED_SCHEMA = {
    "sanity": {
        "type": "number",
        "min": 0,
        "max": 100,
        "initial": 100,
        "display": {"kind": "meter", "label": "Sanity"},
    },
    "clock": {"type": "number", "initial": 0},
}


@pytest.fixture
async def scenario_id(db_session: AsyncSession) -> uuid.UUID:
    creator = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    return created.scenario_id


async def _add_condition(session: AsyncSession, scenario_id, **fields) -> None:
    await ConditionRepo(session).create(
        ScenarioCondition(
            scenario_id=scenario_id,
            label="c",
            narrator_instruction="x",
            **fields,
        )
    )


async def test_status_hud_counts_leftover_display_hints(db_session, scenario_id):
    scenario = await ScenarioRepo(db_session).get_by_id(scenario_id)
    scenario.state_schema = HINTED_SCHEMA
    await db_session.flush()

    assert await count_tool_rows(db_session, "status_hud", scenario_id) == 1


async def test_status_hud_counts_nothing_without_hints(db_session, scenario_id):
    assert await count_tool_rows(db_session, "status_hud", scenario_id) == 0


async def test_atmosphere_counts_only_conditions_with_a_cue(db_session, scenario_id):
    await _add_condition(db_session, scenario_id, sensory_cue="phone_ring")
    await _add_condition(db_session, scenario_id)

    assert await count_tool_rows(db_session, "atmosphere", scenario_id) == 1


async def test_an_unknown_tool_counts_nothing(db_session, scenario_id):
    assert await count_tool_rows(db_session, "nope", scenario_id) == 0
