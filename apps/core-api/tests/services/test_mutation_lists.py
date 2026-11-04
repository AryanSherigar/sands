"""Multi-mutation and fire-once authoring for conditions (Core API side)."""

import uuid

import pytest
from app.db.models.user import User
from app.models.condition import (
    MAX_MUTATIONS_PER_LIST,
    ConditionCreate,
    ConditionUpdate,
    StateMutation,
    effective_mutations,
)
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.condition_service import ConditionService
from app.services.scenario_service import ScenarioService
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession


def _set(path: str, value: object) -> StateMutation:
    return StateMutation(path=path, op="set", value=value)


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    scenario_service = ScenarioService(ScenarioRepo(db_session))
    created = await scenario_service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    return await scenario_service.update_scenario(
        created.scenario_id,
        creator.user_id,
        ScenarioUpdate(
            state_schema={
                "sanity": {"type": "number"},
                "alarm": {"type": "boolean"},
                "clock": {"type": "number"},
            }
        ),
    )


@pytest.fixture
def condition_service(db_session: AsyncSession) -> ConditionService:
    return ConditionService(
        ConditionRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )


def _create(**overrides) -> ConditionCreate:
    base = {
        "label": "Alarm",
        "condition_expression": {"field": "clock", "op": ">=", "value": 5},
        "narrator_instruction": "The alarm sounds.",
    }
    base.update(overrides)
    return ConditionCreate(**base)


def test_effective_mutations_prefers_the_list():
    assert effective_mutations({"path": "a"}, [{"path": "b"}, {"path": "c"}]) == [
        {"path": "b"},
        {"path": "c"},
    ]


def test_effective_mutations_falls_back_to_the_legacy_single():
    assert effective_mutations({"path": "a"}, []) == [{"path": "a"}]
    assert effective_mutations(None, None) == []


def test_create_rejects_more_than_the_cap():
    too_many = [_set("sanity", 1)] * (MAX_MUTATIONS_PER_LIST + 1)

    with pytest.raises(ValidationError):
        _create(state_mutations=too_many)


def test_create_rejects_both_legacy_and_list_shapes():
    with pytest.raises(ValidationError):
        _create(state_mutation=_set("sanity", 1), state_mutations=[_set("alarm", True)])


async def test_list_shape_is_persisted_in_order_and_exposed_with_legacy_first(
    condition_service, master_scenario, creator
):
    result = await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        _create(state_mutations=[_set("sanity", 10), _set("alarm", True)]),
    )

    assert [m.path for m in result.state_mutations] == ["sanity", "alarm"]
    assert result.state_mutation is not None
    assert result.state_mutation["path"] == "sanity"


async def test_legacy_single_is_normalised_into_the_list_and_column_cleared(
    db_session, condition_service, master_scenario, creator
):
    result = await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        _create(state_mutation=_set("sanity", 3)),
    )
    stored = await ConditionRepo(db_session).get_by_id(result.condition_id)

    assert stored.state_mutation is None
    assert stored.state_mutations == [{"path": "sanity", "op": "set", "value": 3}]
    assert [m.path for m in result.state_mutations] == ["sanity"]
    assert result.state_mutation["path"] == "sanity"


async def test_each_list_path_is_validated_against_the_schema(
    condition_service, master_scenario, creator
):
    from app.exceptions.condition_exceptions import ConditionValidationError

    with pytest.raises(ConditionValidationError):
        await condition_service.create_condition(
            master_scenario.scenario_id,
            creator.user_id,
            _create(state_mutations=[_set("sanity", 1), _set("no_such_field", 1)]),
        )


async def test_is_one_shot_defaults_false_and_round_trips(
    condition_service, master_scenario, creator
):
    default = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _create()
    )
    once = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _create(is_one_shot=True)
    )

    assert default.is_one_shot is False
    assert once.is_one_shot is True


async def test_update_replaces_the_list_and_normalises_a_legacy_patch(
    condition_service, master_scenario, creator
):
    created = await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        _create(state_mutations=[_set("sanity", 1), _set("alarm", True)]),
    )

    listed = await condition_service.update_condition(
        master_scenario.scenario_id,
        created.condition_id,
        creator.user_id,
        ConditionUpdate(state_mutations=[_set("clock", 9)]),
    )
    legacy = await condition_service.update_condition(
        master_scenario.scenario_id,
        created.condition_id,
        creator.user_id,
        ConditionUpdate(state_mutation=_set("alarm", False)),
    )

    assert [m.path for m in listed.state_mutations] == ["clock"]
    assert [m.path for m in legacy.state_mutations] == ["alarm"]


async def test_update_can_set_one_shot(condition_service, master_scenario, creator):
    created = await condition_service.create_condition(
        master_scenario.scenario_id, creator.user_id, _create()
    )

    updated = await condition_service.update_condition(
        master_scenario.scenario_id,
        created.condition_id,
        creator.user_id,
        ConditionUpdate(is_one_shot=True),
    )

    assert updated.is_one_shot is True


async def test_duplicate_preserves_mutation_lists_and_one_shot(
    db_session, condition_service, master_scenario, creator
):
    await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        _create(
            state_mutations=[_set("sanity", 1), _set("alarm", True)], is_one_shot=True
        ),
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await ConditionRepo(db_session).list_by_scenario(copy.scenario_id)

    assert [m["path"] for m in copied[0].state_mutations] == ["sanity", "alarm"]
    assert copied[0].is_one_shot is True


async def test_new_snapshot_carries_condition_lists_and_one_shot(
    db_session, condition_service, master_scenario, creator
):
    from app.models.playthrough import PlaythroughCreate
    from app.repositories.playthrough_repo import PlaythroughRepo
    from tests.services.test_tool_snapshot import _make_service

    await condition_service.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        _create(
            state_mutations=[_set("sanity", 1), _set("alarm", True)], is_one_shot=True
        ),
    )
    scenario = await ScenarioRepo(db_session).get_by_id(master_scenario.scenario_id)
    scenario.status = "published"
    await db_session.flush()

    result = await _make_service(db_session).create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    condition = stored.scenario_snapshot["scenario_conditions"][0]

    assert [m["path"] for m in condition["state_mutations"]] == ["sanity", "alarm"]
    assert condition["is_one_shot"] is True
    assert condition["state_mutation"] is None
