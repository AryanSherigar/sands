"""Integration tests for SheetRuleService and the rule_sheet snapshot/response."""

import uuid

import pytest
from app.db.models.user import User
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioAlreadyPublishingError,
)
from app.exceptions.sheet_rule_exceptions import (
    ReservedStateKeyError,
    SheetRuleConflictError,
    SheetRuleModeError,
    SheetRuleNotFoundError,
)
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.models.sheet_rule import SheetRuleCreate, SheetRuleUpdate
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_service import ScenarioService
from app.services.sheet_rule_service import SheetRuleService
from app.tools.data_counters import count_tool_rows
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_rule_check_service import _enable, _start

STATE_SCHEMA = {"clock": {"type": "number", "initial": 0}}


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
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
    await _enable(db_session, updated.scenario_id, creator, ["rule_sheet"])
    return updated


@pytest.fixture
def service(db_session: AsyncSession) -> SheetRuleService:
    return SheetRuleService(SheetRuleRepo(db_session), ScenarioRepo(db_session))


def _rule(key: str = "r1", number: int = 1, **overrides) -> SheetRuleCreate:
    base = {"key": key, "number": number, "text": f"Rule {number}: be quiet."}
    base.update(overrides)
    return SheetRuleCreate(**base)


async def test_create_and_read_back(service, master_scenario, creator):
    created = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule(source_style="pencil")
    )

    fetched = await service.get_rule(
        master_scenario.scenario_id, created.rule_id, creator.user_id
    )

    assert fetched.key == "r1"
    assert fetched.source_style == "pencil"


async def test_create_while_the_tool_is_off_names_the_tool(
    db_session, service, master_scenario, creator
):
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    with pytest.raises(ToolNotEnabledError) as raised:
        await service.create_rule(master_scenario.scenario_id, creator.user_id, _rule())

    assert raised.value.tool_key == "rule_sheet"


async def test_listing_and_deleting_are_allowed_while_the_tool_is_off(
    db_session, service, master_scenario, creator
):
    created = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule()
    )
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    listed = await service.list_rules(master_scenario.scenario_id, creator.user_id)
    await service.delete_rule(
        master_scenario.scenario_id, created.rule_id, creator.user_id
    )

    assert len(listed) == 1
    assert await service.list_rules(master_scenario.scenario_id, creator.user_id) == []


async def test_duplicate_key_or_number_is_a_conflict(service, master_scenario, creator):
    await service.create_rule(master_scenario.scenario_id, creator.user_id, _rule())

    with pytest.raises(SheetRuleConflictError):
        await service.create_rule(
            master_scenario.scenario_id, creator.user_id, _rule(number=2)
        )
    with pytest.raises(SheetRuleConflictError):
        await service.create_rule(
            master_scenario.scenario_id, creator.user_id, _rule(key="r2")
        )


async def test_update_changes_fields_and_guards_number_conflicts(
    service, master_scenario, creator
):
    first = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule()
    )
    await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("r2", 2)
    )

    updated = await service.update_rule(
        master_scenario.scenario_id,
        first.rule_id,
        creator.user_id,
        SheetRuleUpdate(text="New wording.", is_ai_flaggable=True),
    )
    with pytest.raises(SheetRuleConflictError):
        await service.update_rule(
            master_scenario.scenario_id,
            first.rule_id,
            creator.user_id,
            SheetRuleUpdate(number=2),
        )

    assert updated.text == "New wording."
    assert updated.is_ai_flaggable is True


async def test_updating_a_rule_to_its_own_number_is_not_a_conflict(
    service, master_scenario, creator
):
    first = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule()
    )

    updated = await service.update_rule(
        master_scenario.scenario_id,
        first.rule_id,
        creator.user_id,
        SheetRuleUpdate(number=1, text="Same number."),
    )

    assert updated.number == 1


async def test_non_owner_newbie_and_publishing_are_refused(
    db_session, service, master_scenario, creator
):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Stranger"
    )
    newbie = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Tale", mode="newbie", complexity_tier="newbie"),
    )

    with pytest.raises(ScenarioAccessDeniedError):
        await service.create_rule(
            master_scenario.scenario_id, stranger.user_id, _rule()
        )
    with pytest.raises(SheetRuleModeError):
        await service.create_rule(newbie.scenario_id, creator.user_id, _rule())
    scenario = await ScenarioRepo(db_session).get_by_id(master_scenario.scenario_id)
    scenario.status = "publishing"
    await db_session.flush()
    with pytest.raises(ScenarioAlreadyPublishingError):
        await service.create_rule(master_scenario.scenario_id, creator.user_id, _rule())


async def test_rules_of_another_scenario_are_not_found(
    db_session, service, master_scenario, creator
):
    other = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Other", mode="master", complexity_tier="master"),
    )
    created = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule()
    )

    with pytest.raises(SheetRuleNotFoundError):
        await service.get_rule(other.scenario_id, created.rule_id, creator.user_id)


async def test_reorder_assigns_display_order_in_one_pass(
    service, master_scenario, creator
):
    first = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("a", 1)
    )
    second = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("b", 2)
    )

    reordered = await service.reorder_rules(
        master_scenario.scenario_id,
        creator.user_id,
        [second.rule_id, first.rule_id],
    )

    assert [rule.key for rule in reordered] == ["b", "a"]


async def test_reorder_with_an_unknown_id_is_not_found(
    service, master_scenario, creator
):
    with pytest.raises(SheetRuleNotFoundError):
        await service.reorder_rules(
            master_scenario.scenario_id, creator.user_id, [uuid.uuid4()]
        )


async def test_snapshot_pins_rules_and_injects_hidden_state_fields(
    db_session, service, master_scenario, creator
):
    await service.create_rule(
        master_scenario.scenario_id,
        creator.user_id,
        _rule("r1", 1, initial_status="unrevealed", is_ai_flaggable=True),
    )
    await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("r2", 2)
    )

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    snapshot = stored.scenario_snapshot
    schema = snapshot["state_schema"]

    assert [rule["key"] for rule in snapshot["sheet_rules"]] == ["r1", "r2"]
    assert schema["rule_status"]["hidden"] is True
    assert schema["rule_status"]["fields"]["r1"]["initial"] == "unrevealed"
    assert list(schema["rule_flags"]["fields"]) == ["r1"]
    assert "clock" in schema
    assert stored.state["rule_status"] == {"r1": "unrevealed", "r2": "intact"}
    assert stored.state["rule_flags"] == {"r1": False}


async def test_the_browser_never_sees_status_unrevealed_text_or_hidden_schema(
    db_session, service, master_scenario, creator
):
    await service.create_rule(
        master_scenario.scenario_id,
        creator.user_id,
        _rule("r1", 1, text="Always answer.", initial_status="unrevealed"),
    )
    await service.create_rule(
        master_scenario.scenario_id,
        creator.user_id,
        _rule("r2", 2, text="Never open the cage."),
    )

    result = await _start(db_session, creator, master_scenario.scenario_id)
    dumped = result.model_dump_json()

    assert "Always answer." not in dumped
    assert "rule_status" not in dumped
    assert "rule_flags" not in dumped
    assert "sheet_rules" not in dumped
    assert [item.key for item in result.rule_sheet] == ["r2"]
    assert result.rule_sheet[0].text == "Never open the cage."


async def test_no_rules_gives_an_empty_sheet_and_no_injected_roots(
    db_session, master_scenario, creator
):
    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert result.rule_sheet == []
    assert "rule_status" not in stored.scenario_snapshot["state_schema"]


async def test_the_tool_off_contributes_nothing(
    db_session, service, master_scenario, creator
):
    await service.create_rule(master_scenario.scenario_id, creator.user_id, _rule())
    await _enable(db_session, master_scenario.scenario_id, creator, [])

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert "sheet_rules" not in stored.scenario_snapshot
    assert "rule_status" not in stored.scenario_snapshot["state_schema"]
    assert result.rule_sheet == []


async def test_a_declared_reserved_root_is_rejected_on_schema_update(
    db_session, master_scenario, creator
):
    with pytest.raises(ReservedStateKeyError):
        await ScenarioService(ScenarioRepo(db_session)).update_scenario(
            master_scenario.scenario_id,
            creator.user_id,
            ScenarioUpdate(state_schema={"rule_status": {"type": "object"}}),
        )


async def test_enabling_the_tool_over_a_declared_root_is_rejected(db_session, creator):
    scenarios = ScenarioService(ScenarioRepo(db_session))
    created = await scenarios.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Old", mode="master", complexity_tier="master"),
    )
    await scenarios.update_scenario(
        created.scenario_id,
        creator.user_id,
        ScenarioUpdate(state_schema={"rule_flags": {"type": "object"}}),
    )

    with pytest.raises(ReservedStateKeyError):
        await _enable(db_session, created.scenario_id, creator, ["rule_sheet"])


async def test_duplicate_preserves_sheet_rules(
    db_session, service, master_scenario, creator
):
    await service.create_rule(
        master_scenario.scenario_id,
        creator.user_id,
        _rule(corrupted_text="Rule 1: be... quiet.", display_order=4),
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await SheetRuleRepo(db_session).list_by_scenario(copy.scenario_id)

    assert [(r.key, r.display_order) for r in copied] == [("r1", 4)]
    assert copied[0].corrupted_text == "Rule 1: be... quiet."


async def test_inert_count_reports_rules_of_a_disabled_tool(
    db_session, service, master_scenario, creator
):
    await service.create_rule(master_scenario.scenario_id, creator.user_id, _rule())
    await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("r2", 2)
    )

    count = await count_tool_rows(db_session, "rule_sheet", master_scenario.scenario_id)

    assert count == 2


async def test_conditions_and_checks_may_reference_rule_status(
    db_session, service, master_scenario, creator
):
    from app.models.condition import ConditionCreate, StateMutation
    from app.repositories.condition_repo import ConditionRepo
    from app.repositories.entity_repo import EntityRepo
    from app.services.condition_service import ConditionService

    conditions = ConditionService(
        ConditionRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )

    created = await conditions.create_condition(
        master_scenario.scenario_id,
        creator.user_id,
        ConditionCreate(
            label="R2 broken",
            condition_expression={
                "field": "rule_status.r2",
                "op": "==",
                "value": "violated",
            },
            narrator_instruction="Punish it.",
            state_mutations=[
                StateMutation(path="rule_flags.r2", op="set", value=False)
            ],
        ),
    )

    assert created.label == "R2 broken"


async def test_a_rule_sharing_its_number_with_a_sibling_stays_editable(
    db_session, service, master_scenario, creator
):
    """A generator may author alternate rows for one printed rule; editing one
    without renumbering it must not trip over its sibling."""
    first = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule()
    )
    sibling = await service.create_rule(
        master_scenario.scenario_id, creator.user_id, _rule("r1_alt", 2)
    )
    row = await service.sheet_rule_repo.get_by_id(sibling.rule_id)
    row.number = first.number
    await db_session.flush()

    updated = await service.update_rule(
        master_scenario.scenario_id,
        sibling.rule_id,
        creator.user_id,
        SheetRuleUpdate(number=first.number, text="Edited alternate."),
    )

    assert updated.text == "Edited alternate."
    assert updated.number == first.number
