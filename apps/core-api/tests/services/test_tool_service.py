"""Integration tests for ToolService against the real test Postgres."""

import uuid

import pytest
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioAlreadyPublishingError,
    ScenarioNotFoundError,
)
from app.exceptions.tool_exceptions import (
    ToolNotEnabledError,
    ToolRequiredByError,
    ToolsRequireMasterModeError,
    UnknownToolError,
)
from app.models.scenario import ScenarioCreate
from app.models.tools import ToolsUpdate
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_service import ScenarioService
from app.services.tool_service import ToolService, ensure_tool_enabled
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _make_scenario(db_session: AsyncSession, creator: User, mode: str):
    return await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="Night Desk",
            mode=mode,
            complexity_tier=mode,
            player_count_support="solo",
        ),
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    return await _make_scenario(db_session, creator, "master")


def _service(db_session: AsyncSession, counts: dict[str, int] | None = None):
    async def count_rows(tool_key: str, scenario_id: uuid.UUID) -> int:
        return (counts or {}).get(tool_key, 0)

    return ToolService(ScenarioRepo(db_session), count_rows)


async def test_new_scenario_reports_no_tools(db_session, creator, master_scenario):
    result = await _service(db_session).get_tools(
        master_scenario.scenario_id, creator.user_id
    )

    assert result.enabled_tools == []
    assert result.auto_enabled == []
    assert result.inert_data == {}


async def test_enable_round_trip_persists_and_returns_registry_order(
    db_session, creator, master_scenario
):
    service = _service(db_session)

    updated = await service.update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["composure", "rule_checks"]),
    )
    reread = await service.get_tools(master_scenario.scenario_id, creator.user_id)

    assert updated.enabled_tools == ["rule_checks", "composure"]
    assert reread.enabled_tools == ["rule_checks", "composure"]


async def test_enabling_atmosphere_auto_enables_status_hud(
    db_session, creator, master_scenario
):
    result = await _service(db_session).update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["atmosphere"]),
    )

    assert result.enabled_tools == ["status_hud", "atmosphere"]
    assert result.auto_enabled == ["status_hud"]


async def test_disabling_required_tool_is_rejected_naming_dependent(
    db_session, creator, master_scenario
):
    service = _service(db_session)
    await service.update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["atmosphere"]),
    )

    with pytest.raises(ToolRequiredByError) as raised:
        await service.update_tools(
            master_scenario.scenario_id,
            creator.user_id,
            ToolsUpdate(enabled_tools=["atmosphere"]),
        )

    assert raised.value.dependents == ["atmosphere"]


async def test_disabling_both_together_is_allowed(db_session, creator, master_scenario):
    service = _service(db_session)
    await service.update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["atmosphere"]),
    )

    result = await service.update_tools(
        master_scenario.scenario_id, creator.user_id, ToolsUpdate(enabled_tools=[])
    )

    assert result.enabled_tools == []


async def test_unknown_key_is_rejected(db_session, creator, master_scenario):
    with pytest.raises(UnknownToolError):
        await _service(db_session).update_tools(
            master_scenario.scenario_id,
            creator.user_id,
            ToolsUpdate(enabled_tools=["teleporter"]),
        )


async def test_non_owner_is_denied(db_session, master_scenario):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    with pytest.raises(ScenarioAccessDeniedError):
        await _service(db_session).update_tools(
            master_scenario.scenario_id,
            stranger.user_id,
            ToolsUpdate(enabled_tools=["composure"]),
        )


async def test_missing_scenario_is_not_found(db_session, creator):
    with pytest.raises(ScenarioNotFoundError):
        await _service(db_session).get_tools(uuid.uuid4(), creator.user_id)


async def test_newbie_scenario_rejects_non_empty_list(db_session, creator):
    newbie = await _make_scenario(db_session, creator, "newbie")

    with pytest.raises(ToolsRequireMasterModeError):
        await _service(db_session).update_tools(
            newbie.scenario_id,
            creator.user_id,
            ToolsUpdate(enabled_tools=["composure"]),
        )


async def test_newbie_scenario_accepts_empty_list(db_session, creator):
    newbie = await _make_scenario(db_session, creator, "newbie")

    result = await _service(db_session).update_tools(
        newbie.scenario_id, creator.user_id, ToolsUpdate(enabled_tools=[])
    )

    assert result.enabled_tools == []


async def test_publishing_scenario_rejects_writes(db_session, creator, master_scenario):
    scenario = await ScenarioRepo(db_session).get_by_id(master_scenario.scenario_id)
    scenario.status = "publishing"
    await db_session.flush()

    with pytest.raises(ScenarioAlreadyPublishingError):
        await _service(db_session).update_tools(
            master_scenario.scenario_id,
            creator.user_id,
            ToolsUpdate(enabled_tools=["composure"]),
        )


async def test_disabled_tool_with_rows_reports_inert_counts(
    db_session, creator, master_scenario
):
    service = _service(db_session, {"rule_checks": 3, "composure": 2})
    await service.update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["rule_checks", "composure"]),
    )

    result = await service.update_tools(
        master_scenario.scenario_id,
        creator.user_id,
        ToolsUpdate(enabled_tools=["composure"]),
    )

    assert result.inert_data == {"rule_checks": 3}


def test_ensure_tool_enabled_raises_naming_the_tool_when_off():
    scenario = Scenario(enabled_tools=["composure"])

    ensure_tool_enabled(scenario, "composure")
    with pytest.raises(ToolNotEnabledError) as raised:
        ensure_tool_enabled(scenario, "atmosphere")

    assert raised.value.tool_key == "atmosphere"
