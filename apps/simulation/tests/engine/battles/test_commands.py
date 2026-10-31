import pytest
from app.engine.battles.waves import advance_wave
from app.engine.campaign import begin_campaign, resume_campaign
from app.engine.commands.application import accept_command
from app.engine.hashing import world_hash
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import CommandStatus, SetPlanCommand, TakeCommandCommand
from app.models.orders import (
    DisbandArmyOrder,
    MoveArmyOrder,
    RaiseArmyOrder,
    SetPayOrder,
    SetTaxRateOrder,
)
from app.models.world_battle import BattleControlMode, StandingPlan
from app.models.world_state import WorldState
from strategy_contracts.battle import Formation
from strategy_contracts.enums import PayLevel, TaxRate, TroopType
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import ATTACKER
from tests.engine.battles.test_campaign import accept, opened


def test_impossible_levy_and_unreachable_move_cost_zero() -> None:
    world, scenario = opened()
    before = world_hash(world)
    impossible = RaiseArmyOrder(
        faction_id=ATTACKER, region_id="home_a", troops={TroopType.INFANTRY: 99999}
    )
    with pytest.raises(SimulationServiceError):
        accept(world, scenario, impossible)
    unreachable = MoveArmyOrder(
        faction_id=ATTACKER, army_id="army_a", to_region_id="home_a"
    )
    with pytest.raises(SimulationServiceError):
        accept(world, scenario, unreachable)
    assert world_hash(world) == before


def test_engaged_disband_is_rejected_and_urgent_pay_applies_after_waves() -> None:
    world, scenario = opened()
    with pytest.raises(SimulationServiceError):
        accept(world, scenario, DisbandArmyOrder(faction_id=ATTACKER, army_id="army_a"))
    result = accept(
        world,
        scenario,
        SetPayOrder(faction_id=ATTACKER, army_id="army_a", pay_level=PayLevel.REDUCED),
    )
    world = result.world
    assert world.armies["army_a"].pay_level == PayLevel.FULL
    for wave in range(1, 5):
        world = advance_wave(world, scenario, expected_turn=0, expected_wave=wave).world
    finished = resume_campaign(world, scenario, {})
    assert finished.world.armies["army_a"].pay_level == PayLevel.REDUCED
    assert finished.world.accepted_commands[0].status == CommandStatus.APPLIED
    assert sum(event.kind == "pay_set" for event in finished.events) == 1


def test_changed_command_id_conflicts_without_spending() -> None:
    world, scenario = opened()
    first = SetTaxRateOrder(faction_id=ATTACKER, tax_rate=TaxRate.HIGH)
    accepted = accept(world, scenario, first)
    before = world_hash(accepted.world)
    with pytest.raises(SimulationServiceError):
        accept(
            accepted.world,
            scenario,
            SetTaxRateOrder(faction_id=ATTACKER, tax_rate=TaxRate.LOW),
        )
    assert world_hash(accepted.world) == before


def test_failed_deferred_order_never_resurrects_or_charges_again() -> None:
    from tests.engine.battles.test_waves import two_battles

    world, scenario = two_battles()
    accepted = accept(
        world,
        scenario,
        MoveArmyOrder(
            faction_id=ATTACKER, army_id="army_house_a_1", to_region_id="common"
        ),
    )
    world = accepted.world
    for wave in range(1, 5):
        world = advance_wave(world, scenario, expected_turn=0, expected_wave=wave).world
    completed = resume_campaign(world, scenario, {}).world
    second = begin_campaign(completed, scenario).world
    assert second.accepted_commands[0].status == CommandStatus.FAILED
    assert second.accepted_commands[0].failure_reason == "command_unavailable"
    assert second.factions[ATTACKER].orders_remaining == scenario.tuning.orders_per_turn


def test_planning_commands_use_same_ledger_and_apply_at_owning_phase() -> None:
    from tests.engine.battles.builders import battle_fixture

    world, scenario = battle_fixture()
    payload = SetTaxRateOrder(faction_id=ATTACKER, tax_rate=TaxRate.HIGH)
    accepted = accept_command(
        world,
        scenario,
        payload,
        command_id="planning",
        operation_id="planning",
        actor_id="owner",
        faction_id=ATTACKER,
        expected_turn=0,
        expected_wave=0,
    )
    result = begin_campaign(accepted.world, scenario)
    assert result.world.factions[ATTACKER].tax_rate == TaxRate.HIGH
    assert result.world.accepted_commands[0].status == CommandStatus.APPLIED


def test_noop_plan_cannot_replace_an_irrevocable_instruction_slot() -> None:
    world, scenario = opened()
    plan = StandingPlan(formation=Formation.DEFENSIVE)
    first = accept(
        world,
        scenario,
        SetPlanCommand(faction_id=ATTACKER, battle_id="battle_1", plan=plan),
    )
    current = world.battles[0].contingents[ATTACKER].plan
    with pytest.raises(SimulationServiceError):
        accept(
            first.world,
            scenario,
            SetPlanCommand(faction_id=ATTACKER, battle_id="battle_1", plan=current),
            identity="noop",
        )


def test_unavailable_tactic_has_observer_safe_domain_error() -> None:
    from strategy_contracts.battle import Tactic

    world, scenario = opened()
    payload = SetPlanCommand(
        faction_id=ATTACKER,
        battle_id="battle_1",
        plan=StandingPlan(tactic=Tactic.FLANK),
    )
    with pytest.raises(SimulationServiceError) as error:
        accept(world, scenario, payload)
    assert error.value.status_code == 422
    assert error.value.code == "unsupported_tactic"


def test_forest_flank_requires_forest_terrain() -> None:
    from strategy_contracts.battle import Tactic

    world, scenario = opened()
    payload = SetPlanCommand(
        faction_id=ATTACKER,
        battle_id="battle_1",
        plan=StandingPlan(tactic=Tactic.FOREST_FLANK),
    )

    with pytest.raises(SimulationServiceError) as error:
        accept(world, scenario, payload)

    assert error.value.code == "unsupported_tactic"


def test_take_command_is_free_and_persists_after_the_first_wave() -> None:
    world, scenario = opened()
    before = world.factions[ATTACKER].orders_remaining
    accepted = accept(
        world,
        scenario,
        TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1"),
    )

    resolved = advance_wave(accepted.world, scenario, expected_turn=0, expected_wave=1)

    assert resolved.world.factions[ATTACKER].orders_remaining == before
    assert resolved.world.battles[0].control_mode is BattleControlMode.PLAYER


def test_second_take_command_is_rejected_in_the_same_turn() -> None:
    from tests.engine.battles.test_waves import two_battles

    world, scenario = two_battles()
    first = accept(
        world,
        scenario,
        TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1"),
    )

    with pytest.raises(SimulationServiceError) as error:
        accept(
            first.world,
            scenario,
            TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_2"),
            identity="take_second",
        )

    assert error.value.code == "control_limit"


@pytest.fixture
def clean_world() -> WorldState:
    world, _ = opened()
    return world


@pytest.fixture
def test_scenario() -> StrategyScenario:
    _, scenario = opened()
    return scenario


def test_war_council_tactical_commands_cost_zero_mandates(
    clean_world: WorldState,
    test_scenario: StrategyScenario,
) -> None:
    from app.engine.commands.budget import command_cost
    from app.models.battle_command import (
        CommitReservesCommand,
        SetPlanCommand,
        SurrenderCommand,
        WithdrawCommand,
    )
    from app.models.world_battle import StandingPlan

    faction_id = "f_player"
    battle_id = "b_test_battle"

    plan_cmd = SetPlanCommand(
        faction_id=faction_id,
        battle_id=battle_id,
        plan=StandingPlan(),
    )
    reserve_cmd = CommitReservesCommand(
        faction_id=faction_id,
        battle_id=battle_id,
    )
    withdraw_cmd = WithdrawCommand(
        faction_id=faction_id,
        battle_id=battle_id,
    )
    surrender_cmd = SurrenderCommand(
        faction_id=faction_id,
        battle_id=battle_id,
    )

    assert command_cost(plan_cmd, test_scenario, clean_world) == 0
    assert command_cost(reserve_cmd, test_scenario, clean_world) == 0
    assert command_cost(withdraw_cmd, test_scenario, clean_world) == 0
    assert command_cost(surrender_cmd, test_scenario, clean_world) == 0
