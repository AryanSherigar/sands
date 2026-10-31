import pytest
from app.engine.campaign import advance_campaign, begin_campaign
from app.engine.commands.application import CommandAcceptance, accept_command
from app.engine.hashing import world_hash
from app.engine.pipeline import TurnResult
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import DelegateBattleCommand, TakeCommandCommand
from app.models.world_battle import BattleControlMode
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import (
    ATTACKER,
    battle_fixture,
    start_battle,
)


def decision_world() -> tuple[TurnResult, StrategyScenario]:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    start_battle(world, scenario)
    return begin_campaign(world, scenario), scenario


def choose(
    world: WorldState,
    scenario: StrategyScenario,
    payload: TakeCommandCommand | DelegateBattleCommand,
) -> CommandAcceptance:
    return accept_command(
        world,
        scenario,
        payload,
        command_id="choice",
        operation_id="choice",
        actor_id="owner",
        faction_id=ATTACKER,
        expected_turn=world.clock.turn,
        expected_wave=1,
    )


def test_decision_checkpoint_survives_reload_and_blocks_damage() -> None:
    opened, scenario = decision_world()
    restored = WorldState.model_validate_json(opened.world.model_dump_json())
    before = world_hash(restored)
    assert restored.progress.waiting_reason == "awaiting_battle_decision"
    with pytest.raises(CommandError):
        advance_campaign(restored, scenario, expected_turn=0, expected_wave=1)
    assert world_hash(restored) == before
    assert restored.battles[0].total_exchanges == 0


def test_choice_applies_before_damage_and_retry_does_not_change_world() -> None:
    opened, scenario = decision_world()
    payload = TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1")
    accepted = choose(opened.world, scenario, payload)
    assert accepted.world.battles[0].control_mode == BattleControlMode.PLAYER
    assert accepted.world.progress.waiting_reason == "awaiting_commands"
    assert accepted.world.battles[0].total_exchanges == 0
    assert choose(accepted.world, scenario, payload).world == accepted.world


def test_delegation_completes_with_bounded_automatic_waves() -> None:
    opened, scenario = decision_world()
    payload = DelegateBattleCommand(faction_id=ATTACKER, battle_id="battle_1")
    selected = choose(opened.world, scenario, payload).world
    advanced = advance_campaign(selected, scenario, expected_turn=0, expected_wave=1)
    assert advanced.result.world.clock.turn == 1
    assert advanced.result.world.progress.phase is None
    assert len(advanced.receipts) == 4


def test_ai_only_battles_complete_without_a_player_checkpoint() -> None:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    world.factions[ATTACKER].is_player = False
    start_battle(world, scenario)
    result = begin_campaign(world, scenario)
    assert result.world.clock.turn == 1
    assert len(result.receipts) == 4
    assert result.world.battles[0].total_exchanges == 4


def test_legacy_world_has_no_new_checkpoint_or_serialized_rule_field() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    result = begin_campaign(world, scenario)
    assert result.world.progress.waiting_reason == "awaiting_commands"
    assert "battle_control_ruleset" not in world.model_dump()


def test_controlled_wave_keeps_waiting_for_player_commands() -> None:
    opened, scenario = decision_world()
    payload = TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1")
    chosen = choose(opened.world, scenario, payload).world
    advanced = advance_campaign(chosen, scenario, expected_turn=0, expected_wave=1)
    assert advanced.result.world.progress.waiting_reason == "awaiting_commands"
    assert advanced.result.world.battles[0].total_exchanges == 1
    assert len(advanced.receipts) == 1


def test_multiple_decisions_block_advancement_until_all_are_answered() -> None:
    from tests.engine.battles.test_waves import two_battles

    world, scenario = two_battles()
    world.battle_control_ruleset = 1
    world.progress.waiting_reason = "awaiting_battle_decision"
    chosen = choose(
        world, scenario, TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1")
    ).world
    assert chosen.progress.waiting_reason == "awaiting_battle_decision"
    with pytest.raises(CommandError):
        advance_campaign(chosen, scenario, expected_turn=0, expected_wave=1)
