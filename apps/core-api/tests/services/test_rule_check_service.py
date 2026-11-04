"""Integration tests for RuleCheckService against the real test Postgres."""

import uuid

import pytest
from app.db.models.user import User
from app.exceptions.rule_check_exceptions import (
    RuleCheckModeError,
    RuleCheckNotFoundError,
    RuleCheckValidationError,
)
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioAlreadyPublishingError,
)
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.models.playthrough import PlaythroughCreate
from app.models.rule_check import RuleCheckCreate, RuleCheckUpdate
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.models.tools import ToolsUpdate
from app.repositories.entity_repo import EntityRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.rule_check_repo import RuleCheckRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.rule_check_service import RuleCheckService
from app.services.scenario_service import ScenarioService
from app.services.tool_service import ToolService
from app.tools.data_counters import count_tool_rows
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_tool_snapshot import _make_service

STATE_SCHEMA = {
    "clock": {"type": "number", "initial": 0},
    "rules": {
        "type": "object",
        "fields": {
            "r3": {
                "type": "enum",
                "options": ["answered", "ignored", "unseen"],
                "initial": "unseen",
            }
        },
    },
    "alarm": {"type": "boolean"},
}


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _enable(db_session, scenario_id, creator: User, tools: list[str]) -> None:
    async def count_rows(tool_key: str, owned_scenario_id: uuid.UUID) -> int:
        return await count_tool_rows(db_session, tool_key, owned_scenario_id)

    await ToolService(ScenarioRepo(db_session), count_rows).update_tools(
        scenario_id, creator.user_id, ToolsUpdate(enabled_tools=tools)
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    scenarios = ScenarioService(ScenarioRepo(db_session))
    created = await scenarios.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    updated = await scenarios.update_scenario(
        created.scenario_id, creator.user_id, ScenarioUpdate(state_schema=STATE_SCHEMA)
    )
    await _enable(db_session, updated.scenario_id, creator, ["rule_checks"])
    return updated


@pytest.fixture
def service(db_session: AsyncSession) -> RuleCheckService:
    return RuleCheckService(
        RuleCheckRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )


def _option(option_id: str, result: str, **overrides) -> dict[str, object]:
    return {"id": option_id, "label": option_id.title(), "result": result, **overrides}


def _create(**overrides) -> RuleCheckCreate:
    base = {
        "label": "03:14 phone",
        "kind": "timed_choice",
        "trigger_condition_expression": {"field": "clock", "op": ">=", "value": 5},
        "result_path": "rules.r3",
        "params": {
            "prompt": "The phone rings.",
            "options": [_option("answer", "answered"), _option("ignore", "ignored")],
            "window_ms": 12000,
            "timeout_result": "ignored",
        },
    }
    base.update(overrides)
    return RuleCheckCreate(**base)


async def test_create_and_read_back(service, master_scenario, creator):
    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create()
    )
    fetched = await service.get_check(
        master_scenario.scenario_id, created.check_id, creator.user_id
    )

    assert fetched.label == "03:14 phone"
    assert fetched.params["window_ms"] == 12000
    assert fetched.result_path == "rules.r3"


async def test_create_while_tool_is_off_names_the_tool(
    db_session, service, master_scenario, creator
):
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    with pytest.raises(ToolNotEnabledError) as raised:
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create()
        )

    assert raised.value.tool_key == "rule_checks"


async def test_listing_is_allowed_while_tool_is_off(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    items = await service.list_checks(master_scenario.scenario_id, creator.user_id)

    assert len(items) == 1


async def test_newbie_scenario_is_rejected(db_session, service, creator):
    newbie = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Tale", mode="newbie", complexity_tier="newbie"),
    )

    with pytest.raises(RuleCheckModeError):
        await service.create_check(newbie.scenario_id, creator.user_id, _create())


async def test_non_owner_is_denied(db_session, service, master_scenario):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    with pytest.raises(ScenarioAccessDeniedError):
        await service.create_check(
            master_scenario.scenario_id, stranger.user_id, _create()
        )


async def test_publishing_scenario_rejects_writes(
    db_session, service, master_scenario, creator
):
    scenario = await ScenarioRepo(db_session).get_by_id(master_scenario.scenario_id)
    scenario.status = "publishing"
    await db_session.flush()

    with pytest.raises(ScenarioAlreadyPublishingError):
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create()
        )


async def test_result_must_be_a_member_of_the_result_path_enum(
    service, master_scenario, creator
):
    params = _create().params
    params["options"][0]["result"] = "sprinted"

    with pytest.raises(RuleCheckValidationError) as raised:
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create(params=params)
        )

    assert "sprinted" in raised.value.message


async def test_timeout_result_must_be_a_member_too(service, master_scenario, creator):
    params = _create().params
    params["timeout_result"] = "fled"

    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create(params=params)
        )


@pytest.mark.parametrize("bad_path", ["rules.missing", "rules", "clock", "nope"])
async def test_result_path_must_be_a_declared_enum_field(
    service, master_scenario, creator, bad_path
):
    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id,
            creator.user_id,
            _create(result_path=bad_path),
        )


async def test_trigger_expression_must_reference_known_fields(
    service, master_scenario, creator
):
    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id,
            creator.user_id,
            _create(
                trigger_condition_expression={"field": "ghost", "op": "==", "value": 1}
            ),
        )


async def test_option_mutation_paths_use_the_full_path_check(
    service, master_scenario, creator
):
    params = _create().params
    params["options"][0]["mutations"] = [
        {"path": "rules.nope", "op": "set", "value": "x"}
    ]

    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create(params=params)
        )


async def test_option_mutation_may_target_a_declared_field(
    service, master_scenario, creator
):
    params = _create().params
    params["options"][0]["mutations"] = [{"path": "alarm", "op": "set", "value": True}]

    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create(params=params)
    )

    assert created.params["options"][0]["mutations"][0]["path"] == "alarm"


async def test_list_is_ordered_by_priority_and_reorder_reassigns(
    service, master_scenario, creator
):
    late = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create(label="late", priority=5)
    )
    early = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create(label="early", priority=1)
    )

    before = await service.list_checks(master_scenario.scenario_id, creator.user_id)
    after = await service.reorder_checks(
        master_scenario.scenario_id,
        creator.user_id,
        [late.check_id, early.check_id],
    )

    assert [c.label for c in before] == ["early", "late"]
    assert [c.label for c in after] == ["late", "early"]


async def test_reorder_reads_the_checks_once_instead_of_once_per_check(
    db_session, service, master_scenario, creator
):
    created = [
        await service.create_check(
            master_scenario.scenario_id,
            creator.user_id,
            _create(label=f"check {index}", priority=index),
        )
        for index in range(6)
    ]
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if "scenario_rule_checks" in statement:
            statements.append(statement)

    engine = db_session.sync_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        reordered = await service.reorder_checks(
            master_scenario.scenario_id,
            creator.user_id,
            [check.check_id for check in reversed(created)],
        )
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert [c.label for c in reordered] == [f"check {i}" for i in reversed(range(6))]
    assert len(statements) <= 4


async def test_reorder_rejects_a_check_of_another_scenario(
    db_session, service, master_scenario, creator
):
    other = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Other", mode="master", complexity_tier="master"),
    )
    await _enable(db_session, other.scenario_id, creator, ["rule_checks"])
    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create()
    )

    with pytest.raises(RuleCheckNotFoundError):
        await service.reorder_checks(
            other.scenario_id, creator.user_id, [created.check_id]
        )


async def test_checks_of_another_scenario_are_not_found(
    db_session, service, master_scenario, creator
):
    other = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Other", mode="master", complexity_tier="master"),
    )
    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create()
    )

    with pytest.raises(RuleCheckNotFoundError):
        await service.get_check(other.scenario_id, created.check_id, creator.user_id)


async def test_update_revalidates_the_merged_check(service, master_scenario, creator):
    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create()
    )
    bad_params = _create().params
    bad_params["timeout_result"] = "fled"

    renamed = await service.update_check(
        master_scenario.scenario_id,
        created.check_id,
        creator.user_id,
        RuleCheckUpdate(label="renamed"),
    )
    with pytest.raises(RuleCheckValidationError):
        await service.update_check(
            master_scenario.scenario_id,
            created.check_id,
            creator.user_id,
            RuleCheckUpdate(params=bad_params),
        )

    assert renamed.label == "renamed"


async def test_delete_removes_the_check(service, master_scenario, creator):
    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create()
    )

    await service.delete_check(
        master_scenario.scenario_id, created.check_id, creator.user_id
    )

    assert await service.list_checks(master_scenario.scenario_id, creator.user_id) == []


async def test_inert_data_counts_rows_of_a_disabled_tool(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())

    async def count_rows(tool_key: str, owned_scenario_id: uuid.UUID) -> int:
        return await count_tool_rows(db_session, tool_key, owned_scenario_id)

    result = await ToolService(ScenarioRepo(db_session), count_rows).update_tools(
        master_scenario.scenario_id, creator.user_id, ToolsUpdate(enabled_tools=[])
    )

    assert result.inert_data == {"rule_checks": 2}


async def _start(db_session, creator: User, scenario_id: uuid.UUID):
    scenario = await ScenarioRepo(db_session).get_by_id(scenario_id)
    scenario.status = "published"
    await db_session.flush()
    return await _make_service(db_session).create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(scenario_id=scenario_id, setup_values={}),
    )


async def test_snapshot_pins_rule_checks_when_the_tool_is_on(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    pinned = stored.scenario_snapshot["rule_checks"]

    assert [c["label"] for c in pinned] == ["03:14 phone"]
    assert pinned[0]["params"]["timeout_result"] == "ignored"
    assert pinned[0]["result_path"] == "rules.r3"


async def test_snapshot_omits_rule_checks_when_the_tool_is_off(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert "rule_checks" not in stored.scenario_snapshot


async def test_client_response_never_carries_rule_checks(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())

    result = await _start(db_session, creator, master_scenario.scenario_id)

    assert "rule_checks" not in result.scenario_snapshot


async def test_response_carries_server_time_ms(db_session, master_scenario, creator):
    result = await _start(db_session, creator, master_scenario.scenario_id)

    assert result.server_time_ms > 1_700_000_000_000


async def test_duplicate_preserves_rule_checks(
    db_session, service, master_scenario, creator
):
    await service.create_check(master_scenario.scenario_id, creator.user_id, _create())

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await RuleCheckRepo(db_session).list_by_scenario(copy.scenario_id)

    assert [c.label for c in copied] == ["03:14 phone"]
    assert copied[0].params["window_ms"] == 12000


def _recall_params(**overrides) -> dict[str, object]:
    base = {
        "prompt": "Which wording was the original rule?",
        "variants": ["Never answer", "Always answer", "Answer once"],
        "correct_index": 1,
        "result_correct": "answered",
        "result_wrong": "ignored",
        "result_timeout": "unseen",
    }
    base.update(overrides)
    return base


async def test_recall_check_is_created_and_snapshotted(
    db_session, service, master_scenario, creator
):
    await service.create_check(
        master_scenario.scenario_id,
        creator.user_id,
        _create(kind="recall", params=_recall_params()),
    )

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    pinned = stored.scenario_snapshot["rule_checks"][0]

    assert pinned["kind"] == "recall"
    assert pinned["params"]["correct_index"] == 1


async def test_recall_results_must_be_members_of_the_enum(
    service, master_scenario, creator
):
    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id,
            creator.user_id,
            _create(kind="recall", params=_recall_params(result_wrong="panicked")),
        )


async def test_hidden_result_must_be_a_member_of_the_enum(
    service, master_scenario, creator
):
    params = _create().params
    params["hidden_result"] = "fled"

    with pytest.raises(RuleCheckValidationError):
        await service.create_check(
            master_scenario.scenario_id, creator.user_id, _create(params=params)
        )


async def test_hidden_result_and_reopens_are_stored(service, master_scenario, creator):
    params = _create().params
    params["hidden_result"] = "unseen"
    params["max_reopens"] = 2
    params["options"][0]["reopens"] = True

    created = await service.create_check(
        master_scenario.scenario_id, creator.user_id, _create(params=params)
    )

    assert created.params["hidden_result"] == "unseen"
    assert created.params["max_reopens"] == 2
    assert created.params["options"][0]["reopens"] is True


RANDOM_SCHEMA = {
    **STATE_SCHEMA,
    "rule_slot": {
        "type": "enum",
        "options": ["r4", "r6"],
        "initial_random": ["r4", "r6"],
    },
}


async def test_initial_random_is_drawn_into_the_new_playthroughs_state(
    db_session, master_scenario, creator
):
    scenarios = ScenarioService(ScenarioRepo(db_session))
    await scenarios.update_scenario(
        master_scenario.scenario_id,
        creator.user_id,
        ScenarioUpdate(state_schema=RANDOM_SCHEMA),
    )

    result = await _start(db_session, creator, master_scenario.scenario_id)

    assert result.state["rule_slot"] in ("r4", "r6")
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    assert "initial_random" in stored.scenario_snapshot["state_schema"]["rule_slot"]


async def test_initial_random_is_refused_while_the_tool_is_off(
    db_session, master_scenario, creator
):
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    with pytest.raises(ToolNotEnabledError):
        await ScenarioService(ScenarioRepo(db_session)).update_scenario(
            master_scenario.scenario_id,
            creator.user_id,
            ScenarioUpdate(state_schema=RANDOM_SCHEMA),
        )


async def test_leftover_initial_random_is_stripped_and_not_drawn_when_off(
    db_session, master_scenario, creator
):
    scenarios = ScenarioService(ScenarioRepo(db_session))
    await scenarios.update_scenario(
        master_scenario.scenario_id,
        creator.user_id,
        ScenarioUpdate(state_schema=RANDOM_SCHEMA),
    )
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert "rule_slot" not in result.state
    assert "initial_random" not in stored.scenario_snapshot["state_schema"]["rule_slot"]
