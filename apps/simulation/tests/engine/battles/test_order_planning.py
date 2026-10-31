import pytest
from app.engine.commands.application import CommandAcceptance, accept_command
from app.engine.commands.cancellation import cancel_command
from app.engine.commands.check import CommandCheck, check_command
from app.engine.hashing import world_hash
from app.exceptions.command_exceptions import CommandError
from app.models.api_orders import OrderFlag
from app.models.battle_command import Command
from app.models.orders import RaiseArmyOrder, SetPayOrder, TakeLoanOrder
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from strategy_contracts.enums import PayLevel, TroopType
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import ATTACKER, DEFENDER, battle_fixture

LEVY_SIZE = 40
LEVY_COST = 16
FIRST_REGION = "home_a"
SECOND_REGION = "home_b"
LOAN_SIZE = 30


def planning_world(treasury: int) -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture()
    world.regions[SECOND_REGION].owner_id = ATTACKER
    for region_id in (FIRST_REGION, SECOND_REGION):
        world.regions[region_id].manpower = LEVY_SIZE * 2
    world.factions[ATTACKER].treasury = treasury
    return world, scenario


def plan(
    world: WorldState,
    scenario: StrategyScenario,
    payload: Command,
    identity: str,
) -> CommandAcceptance:
    return accept_command(
        world,
        scenario,
        payload,
        command_id=identity,
        operation_id=identity,
        actor_id="owner",
        faction_id=ATTACKER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )


def levy(region_id: str, size: int = LEVY_SIZE) -> RaiseArmyOrder:
    return RaiseArmyOrder(
        faction_id=ATTACKER, region_id=region_id, troops={TroopType.INFANTRY: size}
    )


def test_unaffordable_order_is_rejected_with_its_specific_reason() -> None:
    world, scenario = planning_world(treasury=LEVY_COST - 1)
    before = world_hash(world)
    with pytest.raises(CommandError) as raised:
        plan(world, scenario, levy(FIRST_REGION), "first")
    assert raised.value.code == "insufficient_funds"
    assert raised.value.status_code == 422
    assert world_hash(world) == before


def test_missing_manpower_reports_manpower_not_a_generic_failure() -> None:
    world, scenario = planning_world(treasury=1000)
    with pytest.raises(CommandError) as raised:
        plan(world, scenario, levy(FIRST_REGION, size=LEVY_SIZE * 3), "first")
    assert raised.value.code == "insufficient_manpower"


def test_queued_spending_counts_against_the_next_order() -> None:
    world, scenario = planning_world(treasury=LEVY_COST + LEVY_COST // 2)
    first = plan(world, scenario, levy(FIRST_REGION), "first")
    points_left = first.world.factions[ATTACKER].orders_remaining
    before = world_hash(first.world)
    with pytest.raises(CommandError) as raised:
        plan(first.world, scenario, levy(SECOND_REGION), "second")
    assert raised.value.code == "insufficient_funds"
    assert first.world.factions[ATTACKER].orders_remaining == points_left
    assert world_hash(first.world) == before


def test_both_orders_pass_when_the_treasury_covers_the_queue() -> None:
    world, scenario = planning_world(treasury=LEVY_COST * 2)
    first = plan(world, scenario, levy(FIRST_REGION), "first")
    second = plan(first.world, scenario, levy(SECOND_REGION), "second")
    assert [item.id for item in second.world.accepted_commands] == ["first", "second"]


def loan(amount: int) -> TakeLoanOrder:
    return TakeLoanOrder(faction_id=ATTACKER, amount=amount)


def cancel(
    world: WorldState,
    scenario: StrategyScenario,
    identity: str,
    faction: str = ATTACKER,
) -> WorldState:
    return cancel_command(
        world,
        scenario,
        identity,
        faction_id=faction,
        expected_turn=world.clock.turn,
    )


def test_removing_an_order_refunds_its_points_and_frees_its_slot() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    full_budget = world.factions[ATTACKER].orders_remaining
    queued = plan(world, scenario, levy(FIRST_REGION), "first").world
    assert queued.factions[ATTACKER].orders_remaining < full_budget
    removed = cancel(queued, scenario, "first")
    assert removed.accepted_commands == []
    assert removed.factions[ATTACKER].orders_remaining == full_budget
    plan(removed, scenario, levy(FIRST_REGION), "again")


def test_removal_leaves_the_input_world_untouched() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    queued = plan(world, scenario, levy(FIRST_REGION), "first").world
    before = world_hash(queued)
    cancel(queued, scenario, "first")
    assert world_hash(queued) == before


def test_unknown_or_foreign_order_cannot_be_removed() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    queued = plan(world, scenario, levy(FIRST_REGION), "first").world
    for identity, faction in (("missing", ATTACKER), ("first", DEFENDER)):
        with pytest.raises(CommandError) as raised:
            cancel(queued, scenario, identity, faction)
        assert (raised.value.code, raised.value.status_code) == ("not_found", 404)


def test_cannot_remove_an_order_another_queued_order_depends_on() -> None:
    world, scenario = planning_world(treasury=0)
    first = plan(world, scenario, loan(LOAN_SIZE), "loan")
    second = plan(first.world, scenario, levy(FIRST_REGION), "levy")
    with pytest.raises(CommandError) as raised:
        cancel(second.world, scenario, "loan")
    assert raised.value.code == "order_has_dependents"
    removable = cancel(second.world, scenario, "levy")
    assert [item.id for item in removable.accepted_commands] == ["loan"]
    assert cancel(removable, scenario, "loan").accepted_commands == []


def test_removal_is_refused_once_the_campaign_has_started() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    queued = plan(world, scenario, levy(FIRST_REGION), "first").world
    queued.progress.phase = PhaseName.BATTLES
    with pytest.raises(CommandError) as raised:
        cancel(queued, scenario, "first")
    assert raised.value.code == "invalid_lifecycle"


def test_order_carried_over_from_an_earlier_turn_is_not_removable() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    queued = plan(world, scenario, levy(FIRST_REGION), "first").world
    queued.accepted_commands[0].accepted_turn = 0
    queued.clock.turn = 1
    queued.accepted_commands[0].execution_turn = 1
    with pytest.raises(CommandError) as raised:
        cancel(queued, scenario, "first")
    assert raised.value.code == "not_cancellable"


def check(
    world: WorldState, scenario: StrategyScenario, payload: Command
) -> CommandCheck:
    return check_command(
        world,
        scenario,
        payload,
        faction_id=ATTACKER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )


def test_check_reports_money_shortage_as_over_budget_without_touching_the_world() -> (
    None
):
    world, scenario = planning_world(treasury=LEVY_COST - 1)
    before = world_hash(world)
    result = check(world, scenario, levy(FIRST_REGION))
    assert (result.flag, result.reason) == (OrderFlag.OVER_BUDGET, "insufficient_funds")
    assert world_hash(world) == before


def test_check_passes_an_affordable_order_and_charges_nothing() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    points = world.factions[ATTACKER].orders_remaining
    result = check(world, scenario, levy(FIRST_REGION))
    assert result.flag is None
    assert result.orders_remaining == points
    assert world.accepted_commands == []


def test_check_flags_missing_command_points() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    world.factions[ATTACKER].orders_remaining = 0
    result = check(world, scenario, levy(FIRST_REGION))
    assert (result.flag, result.reason) == (
        OrderFlag.OVER_BUDGET,
        "insufficient_points",
    )


def test_check_flags_another_factions_army_without_saying_whether_it_exists() -> None:
    world, scenario = planning_world(treasury=LEVY_COST)
    foreign = SetPayOrder(
        faction_id=ATTACKER, army_id="army_b", pay_level=PayLevel.REDUCED
    )
    result = check(world, scenario, foreign)
    assert (result.flag, result.reason) == (OrderFlag.NOT_YOUR_ARMY, "not_found")


def test_check_flags_an_impossible_levy() -> None:
    world, scenario = planning_world(treasury=1000)
    result = check(world, scenario, levy(FIRST_REGION, size=LEVY_SIZE * 3))
    assert (result.flag, result.reason) == (
        OrderFlag.IMPOSSIBLE,
        "insufficient_manpower",
    )
