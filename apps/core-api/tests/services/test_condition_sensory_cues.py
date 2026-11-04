"""Cue columns on conditions are atmosphere-gated and snapshot-stripped when off."""

import uuid

import pytest
from app.db.models.user import User
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.models.condition import ConditionCreate, ConditionUpdate
from app.models.playthrough import PlaythroughCreate
from app.models.scenario import ScenarioCreate
from app.models.tools import ToolsUpdate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.condition_service import ConditionService
from app.services.scenario_service import ScenarioService
from app.services.tool_service import ToolService
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_tool_snapshot import _make_service


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    return await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )


@pytest.fixture
def condition_service(db_session: AsyncSession) -> ConditionService:
    return ConditionService(
        ConditionRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )


async def _enable(db_session: AsyncSession, scenario, creator: User, tools: list[str]):
    async def no_rows(tool_key: str, scenario_id: uuid.UUID) -> int:
        return 0

    await ToolService(ScenarioRepo(db_session), no_rows).update_tools(
        scenario.scenario_id, creator.user_id, ToolsUpdate(enabled_tools=tools)
    )


def _phone(**overrides) -> ConditionCreate:
    return ConditionCreate(
        label="Phone",
        narrator_instruction="The phone rings.",
        sensory_cue="phone_ring",
        silence_duration_ms=1500,
        **overrides,
    )


async def test_setting_a_cue_while_atmosphere_is_off_is_a_409_naming_the_tool(
    condition_service, master_scenario, creator
):
    with pytest.raises(ToolNotEnabledError) as raised:
        await condition_service.create_condition(
            master_scenario.scenario_id, creator.user_id, _phone()
        )

    assert raised.value.tool_key == "atmosphere"


async def test_cue_round_trips_when_atmosphere_is_on(
    db_session, condition_service, master_scenario, creator
):
    await _enable(db_session, master_scenario, creator, ["atmosphere"])

    created = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _phone(cut_ambient=False)
    )

    assert created.sensory_cue == "phone_ring"
    assert created.cut_ambient is False
    assert created.silence_duration_ms == 1500


async def test_condition_without_a_cue_needs_no_tool(
    condition_service, master_scenario, creator
):
    created = await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        ConditionCreate(label="Plain", narrator_instruction="Nothing special."),
    )

    assert created.sensory_cue is None


async def test_update_setting_a_cue_is_gated_too(
    condition_service, master_scenario, creator
):
    created = await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        ConditionCreate(label="Plain", narrator_instruction="Nothing special."),
    )

    with pytest.raises(ToolNotEnabledError):
        await condition_service.update_condition(
            master_scenario.scenario_id,
            created.condition_id,
            creator.user_id,
            ConditionUpdate(sensory_cue="heavy_knock"),
        )


async def test_update_can_clear_a_cue_even_after_the_tool_is_disabled(
    db_session, condition_service, master_scenario, creator
):
    await _enable(db_session, master_scenario, creator, ["atmosphere"])
    created = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _phone()
    )
    await _enable(db_session, master_scenario, creator, [])

    cleared = await condition_service.update_condition(
        master_scenario.scenario_id,
        created.condition_id,
        creator.user_id,
        ConditionUpdate(sensory_cue=None),
    )

    assert cleared.sensory_cue is None


async def _published_playthrough_condition(
    db_session, master_scenario, creator: User
) -> dict[str, object]:
    scenario = await ScenarioRepo(db_session).get_by_id(master_scenario.scenario_id)
    scenario.status = "published"
    await db_session.flush()
    result = await _make_service(db_session).create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    return stored.scenario_snapshot["scenario_conditions"][0]


async def test_snapshot_keeps_cue_fields_when_atmosphere_is_on(
    db_session, condition_service, master_scenario, creator
):
    await _enable(db_session, master_scenario, creator, ["atmosphere"])
    await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _phone()
    )

    condition = await _published_playthrough_condition(
        db_session, master_scenario, creator
    )

    assert condition["sensory_cue"] == "phone_ring"
    assert condition["silence_duration_ms"] == 1500
    assert condition["cut_ambient"] is True


async def test_snapshot_strips_cue_fields_when_atmosphere_is_off_but_data_kept(
    db_session, condition_service, master_scenario, creator
):
    await _enable(db_session, master_scenario, creator, ["atmosphere"])
    created = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _phone()
    )
    await _enable(db_session, master_scenario, creator, [])

    condition = await _published_playthrough_condition(
        db_session, master_scenario, creator
    )
    stored = await ConditionRepo(db_session).get_by_id(created.condition_id)

    for stripped in ("sensory_cue", "cut_ambient", "silence_duration_ms"):
        assert stripped not in condition
    assert stored.sensory_cue == "phone_ring"


async def test_duplicate_preserves_cue_fields(
    db_session, condition_service, master_scenario, creator
):
    await _enable(db_session, master_scenario, creator, ["atmosphere"])
    await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _phone(cut_ambient=False)
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await ConditionRepo(db_session).list_by_scenario(copy.scenario_id)

    assert copied[0].sensory_cue == "phone_ring"
    assert copied[0].cut_ambient is False
    assert copied[0].silence_duration_ms == 1500
