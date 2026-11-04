import pytest
from app.engine.battles.waves import advance_wave
from app.engine.campaign import begin_campaign, campaign_phases
from app.engine.commands.application import CommandAcceptance, accept_command
from app.engine.hashing import world_hash
from app.engine.phases import PhaseCheckpoint, PhaseContext, PhaseResult, ScenePause
from app.engine.pipeline import run_turn
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import Command, SetPlanCommand, SurrenderCommand
from app.models.orders import SetPayOrder, SetTaxRateOrder
from app.models.world_battle import StandingPlan
from app.models.world_events import PHASE_ORDER, PhaseName, TurnStatus
from app.models.world_state import WorldState
from strategy_contracts.battle import Formation, Tactic
from strategy_contracts.enums import PayLevel, TaxRate
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneType

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    start_battle,
)
from tests.engine.test_pipeline import NoopPhase, _event


def opened() -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    start_battle(world, scenario)
    for faction in world.factions.values():
        faction.is_player = True
    return begin_campaign(world, scenario).world, scenario


def accept(
    world: WorldState,
    scenario: StrategyScenario,
    payload: Command,
    identity: str = "cmd",
    faction: str = ATTACKER,
) -> CommandAcceptance:
    return accept_command(
        world,
        scenario,
        payload,
        command_id=identity,
        operation_id=identity,
        actor_id="owner",
        faction_id=faction,
        expected_turn=world.clock.turn,
        expected_wave=world.progress.completed_waves + 1,
    )


def test_checkpoint_commits_but_scene_pause_rolls_back() -> None:
    class CheckpointPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            world.regions["field"].unrest = 77
            return PhaseResult(world, [_event(self.name)], checkpoint=PhaseCheckpoint())

    world, scenario = battle_fixture()
    phases = {name: NoopPhase(name) for name in PHASE_ORDER}
    phases[PhaseName.BATTLES] = CheckpointPhase(PhaseName.BATTLES)
    result = run_turn(world, scenario, [], phases, {}, {})
    assert result.status == TurnStatus.AWAITING_COMMANDS
    assert result.world.regions["field"].unrest == 77
    assert len(result.events) == 1
    assert result.world.progress.phase == PhaseName.BATTLES
    with pytest.raises(SimulationServiceError):
        PhaseResult(
            world, pause=ScenePause(SceneType.EVENT, ()), checkpoint=PhaseCheckpoint()
        )


def test_four_waves_resume_without_repeating_damage_or_economy() -> None:
    world, scenario = opened()
    treasury = world.factions[ATTACKER].treasury
    assert world.progress.completed_waves == 0
    first = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    second = advance_wave(first.world, scenario, expected_turn=0, expected_wave=2)
    assert second.world.battles[0].total_exchanges == 2
    assert second.world.factions[ATTACKER].treasury == treasury
    assert min(event.seq for event in second.events) > max(
        event.seq for event in first.events
    )
    with pytest.raises(SimulationServiceError):
        advance_wave(second.world, scenario, expected_turn=0, expected_wave=2)
    third = advance_wave(second.world, scenario, expected_turn=0, expected_wave=3)
    fourth = advance_wave(third.world, scenario, expected_turn=0, expected_wave=4)
    assert fourth.world.progress.completed_waves == 4
    with pytest.raises(SimulationServiceError):
        advance_wave(fourth.world, scenario, expected_turn=0, expected_wave=5)
    completed = run_turn(fourth.world, scenario, [], campaign_phases(), {}, {})
    assert completed.world.clock.turn == 1
    assert completed.world_hash == world_hash(completed.world)


def test_plan_command_is_free_and_idempotent() -> None:
    world, scenario = opened()
    current = world.battles[0].contingents[ATTACKER].plan
    unchanged = accept(
        world,
        scenario,
        SetPlanCommand(faction_id=ATTACKER, battle_id=BATTLE_ID, plan=current),
    )
    assert unchanged.command is None
    payload = SetPlanCommand(
        faction_id=ATTACKER,
        battle_id=BATTLE_ID,
        plan=StandingPlan(formation=Formation.DEFENSIVE),
    )
    first = accept(world, scenario, payload)
    duplicate = accept(first.world, scenario, payload)
    assert duplicate.world == first.world
    assert (
        first.world.factions[ATTACKER].orders_remaining
        == world.factions[ATTACKER].orders_remaining
    )
    with pytest.raises(SimulationServiceError):
        accept(first.world, scenario, payload, identity="different")


def test_invalid_tactic_and_foreign_surrender_are_free() -> None:
    world, scenario = opened()
    before = world_hash(world)
    invalid = SetPlanCommand(
        faction_id=ATTACKER, battle_id=BATTLE_ID, plan=StandingPlan(tactic=Tactic.FLANK)
    )
    with pytest.raises(SimulationServiceError):
        accept(world, scenario, invalid)
    with pytest.raises(SimulationServiceError):
        accept(
            world, scenario, SurrenderCommand(faction_id=DEFENDER, battle_id=BATTLE_ID)
        )
    assert world_hash(world) == before


def test_surrender_stays_free_when_empire_orders_are_spent() -> None:
    world, scenario = opened()
    world.factions[ATTACKER].orders_remaining = 1
    tax = SetTaxRateOrder(faction_id=ATTACKER, tax_rate=TaxRate.HIGH)
    accepted = accept(world, scenario, tax)
    assert accepted.command.execution_turn == 1
    assert accepted.world.factions[ATTACKER].orders_remaining == 0
    surrendered = accept(
        accepted.world,
        scenario,
        SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID),
        identity="battle",
    )
    assert surrendered.world.factions[ATTACKER].orders_remaining == 0
    pay = SetPayOrder(faction_id=ATTACKER, army_id="army_a", pay_level=PayLevel.FULL)
    world.factions[ATTACKER].orders_remaining = 6
    urgent = accept(world, scenario, pay)
    assert urgent.command.execution_turn == 0


def test_urgent_command_after_second_wave_is_valid() -> None:
    world, scenario = opened()
    for wave in (1, 2):
        world = advance_wave(world, scenario, expected_turn=0, expected_wave=wave).world
    payload = SetPayOrder(
        faction_id=ATTACKER, army_id="army_a", pay_level=PayLevel.REDUCED
    )
    result = accept(world, scenario, payload)
    assert result.command.execution_turn == 0
    assert result.command.execution_wave == 0


def test_second_campaign_retains_plans_applies_deferred_once_and_resets_debt() -> None:
    from app.engine.campaign import resume_campaign
    from app.models.battle_command import CommandStatus

    world, scenario = opened()
    world.factions[ATTACKER].treasury = 10000
    world.factions[DEFENDER].treasury = 10000
    world.factions[ATTACKER].orders_debt = 2
    payload = SetTaxRateOrder(faction_id=ATTACKER, tax_rate=TaxRate.HIGH)
    world = accept(world, scenario, payload).world
    for wave in range(1, 5):
        world = advance_wave(world, scenario, expected_turn=0, expected_wave=wave).world
    completed = resume_campaign(world, scenario, {})
    assert completed.world.factions[ATTACKER].tax_rate != TaxRate.HIGH
    assert (
        completed.world.factions[ATTACKER].orders_remaining
        == scenario.tuning.orders_per_turn - 2
    )
    assert completed.world.factions[ATTACKER].orders_debt == 0
    second = begin_campaign(completed.world, scenario)
    assert second.world.battles[0].exchanges_used == 0
    assert second.world.battles[0].total_exchanges == 4
    for wave in range(1, 5):
        second.world = advance_wave(
            second.world, scenario, expected_turn=1, expected_wave=wave
        ).world
    done = resume_campaign(second.world, scenario, {})
    assert done.world.factions[ATTACKER].tax_rate == TaxRate.HIGH
    assert done.world.accepted_commands[0].status == CommandStatus.APPLIED
    assert (
        done.world.factions[ATTACKER].orders_remaining
        == scenario.tuning.orders_per_turn
    )
    assert sum(event.kind == "income_collected" for event in done.events) == 2


def test_movement_created_contact_initializes_terrain_before_deployment() -> None:
    from app.engine.movement.engagement import open_or_join_battle

    world, scenario = battle_fixture()
    open_or_join_battle(world, "field", ["army_a"], ["army_b"])
    result = begin_campaign(world, scenario)
    assert result.status == TurnStatus.AWAITING_COMMANDS
    assert result.world.battles[0].terrain is not None
    assert result.world.battles[0].contingents[ATTACKER].deployments


@pytest.mark.parametrize("choice", ["shortfall_take_loan", "shortfall_default"])
def test_economy_choice_rollback_then_single_settlement_and_debt_reset(
    choice: str,
) -> None:
    from app.engine.campaign import resume_campaign
    from strategy_contracts.scene import ChoiceOutcome

    from tests.engine.economy.builders import PLAYER, SCENE_ID, make_scenario
    from tests.engine.economy.test_shortfall import _world

    world = _world()
    scenario = make_scenario()
    paused = begin_campaign(world, scenario)
    assert paused.status == TurnStatus.PAUSED
    assert paused.world.factions[PLAYER].treasury == 0
    assert paused.world.clock.turn == 0
    paused.world.progress.pending_scene_id = SCENE_ID
    resumed = resume_campaign(
        paused.world, scenario, {SCENE_ID: ChoiceOutcome(option_id=choice)}
    )
    assert resumed.status == TurnStatus.RESOLVED
    assert resumed.world.clock.turn == 1
    assert sum(event.kind == "income_collected" for event in resumed.events) == 1
    assert resumed.world.factions[PLAYER].orders_debt == 0
    assert (
        resumed.world.factions[PLAYER].orders_remaining
        == scenario.tuning.orders_per_turn - 1
    )
    _assert_shortfall_finances(resumed.world, PLAYER, choice)


def _assert_shortfall_finances(world: WorldState, faction_id: str, choice: str) -> None:
    if choice == "shortfall_take_loan":
        assert len(world.factions[faction_id].loans) == 1
    else:
        assert world.factions[faction_id].credit_strikes == 1


def test_campaign_advance_returns_wave_receipts_and_final_economy_together() -> None:
    from app.engine.campaign import advance_campaign

    world, scenario = opened()
    for wave in range(1, 5):
        transition = advance_campaign(
            world, scenario, expected_turn=0, expected_wave=wave
        )
        world = transition.result.world
        assert len(transition.receipts) == 1
    assert transition.result.status == TurnStatus.RESOLVED
    assert world.clock.turn == 1
    assert (
        sum(
            event.kind == "battle_exchange_resolved"
            for event in transition.result.events
        )
        == 1
    )
    assert (
        sum(event.kind == "income_collected" for event in transition.result.events) == 2
    )


def _withdrawn_campaign() -> tuple[WorldState, StrategyScenario]:
    from app.models.world_battle import BattleStatus, ContingentStatus

    from tests.engine.battles.builders import ALLY, REGION
    from tests.engine.movement.builders import make_army

    world, scenario = battle_fixture(
        extra_armies=[make_army("army_c", ALLY, REGION)], has_routes=True
    )
    start_battle(world, scenario)
    world.progress.is_campaign_active = True
    world.progress.phase = PhaseName.TIME
    world.progress.completed_waves = 4
    world.battles[0].status = BattleStatus.AWAITING_NEXT_TURN
    world.battles[0].contingents[ATTACKER].status = ContingentStatus.WITHDRAWN
    world.armies["army_a"].location_id = "home_a"
    for army in world.armies.values():
        army.fatigue = 30
    return world, scenario


def test_withdrawn_contingent_recovers_with_events_while_allies_keep_fighting() -> None:
    from app.engine.campaign import resume_campaign

    world, scenario = _withdrawn_campaign()
    result = resume_campaign(world, scenario, {})
    assert result.world.armies["army_a"].fatigue == 10
    assert result.world.armies["army_c"].fatigue == 30
    recovery = [
        event for event in result.events if event.kind == "army_fatigue_recovered"
    ]
    assert len(recovery) == 1
    assert recovery[0].cause.subject_ids == ["army_a"]
    assert recovery[0].changes[0].before == 30 and recovery[0].changes[0].after == 10
    assert recovery[0].phase == PhaseName.TIME and recovery[0].seq > 0
    assert recovery[0].turn == 0 and result.world.clock.turn == 1
    assert result.world_hash == world_hash(result.world)
