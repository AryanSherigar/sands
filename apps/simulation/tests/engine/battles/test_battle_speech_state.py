import pytest
from app.engine.battles.control import pending_speeches
from app.engine.battles.speech import complete_speech
from app.engine.campaign import advance_campaign, begin_campaign
from app.engine.commands.application import CommandAcceptance, accept_command
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.battle_command import DelegateBattleCommand, TakeCommandCommand
from app.models.world_battle import BattleSpeechStatus
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import BattleSpeechOutcome

from tests.engine.battles.builders import ATTACKER, battle_fixture, start_battle


def opened_world(speech_ruleset: int) -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture(casualty_rate_percent=1)
    world.battle_control_ruleset = 1
    world.battle_speech_ruleset = speech_ruleset
    start_battle(world, scenario)
    return begin_campaign(world, scenario).world, scenario


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


def take_command(speech_ruleset: int) -> tuple[WorldState, StrategyScenario]:
    world, scenario = opened_world(speech_ruleset)
    payload = TakeCommandCommand(faction_id=ATTACKER, battle_id="battle_1")
    return choose(world, scenario, payload).world, scenario


def test_take_command_creates_pending_speech_when_ruleset_on() -> None:
    world, _ = take_command(speech_ruleset=1)
    assert world.battles[0].speech is not None
    assert world.battles[0].speech.status == BattleSpeechStatus.PENDING
    assert [battle.id for battle in pending_speeches(world)] == ["battle_1"]


def test_take_command_without_ruleset_creates_no_speech() -> None:
    world, _ = take_command(speech_ruleset=0)
    assert world.battles[0].speech is None
    assert pending_speeches(world) == []


def test_delegate_creates_no_speech() -> None:
    world, scenario = opened_world(speech_ruleset=1)
    payload = DelegateBattleCommand(faction_id=ATTACKER, battle_id="battle_1")
    chosen = choose(world, scenario, payload).world
    assert chosen.battles[0].speech is None


def test_advance_is_blocked_until_the_speech_is_done() -> None:
    world, scenario = take_command(speech_ruleset=1)
    with pytest.raises(CampaignProgressError):
        advance_campaign(world, scenario, expected_turn=0, expected_wave=1)
    assert world.battles[0].total_exchanges == 0
    complete_speech(world, "battle_1", BattleSpeechOutcome(morale_delta_percent=0))
    advanced = advance_campaign(world, scenario, expected_turn=0, expected_wave=1)
    assert advanced.result.world.battles[0].total_exchanges == 1


def test_complete_speech_applies_clamped_morale_to_player_army() -> None:
    world, _ = take_command(speech_ruleset=1)
    army_id = world.battles[0].contingents[ATTACKER].army_ids[0]
    world.armies[army_id].morale = 90
    outcome = BattleSpeechOutcome(morale_delta_percent=15)
    changes = complete_speech(world, "battle_1", outcome)
    assert world.armies[army_id].morale == 100
    assert [change.path for change in changes] == [f"armies.{army_id}.morale"]
    assert world.battles[0].speech.status == BattleSpeechStatus.DONE
    assert world.battles[0].speech.outcome == outcome


def test_complete_speech_twice_does_not_apply_morale_twice() -> None:
    world, _ = take_command(speech_ruleset=1)
    army_id = world.battles[0].contingents[ATTACKER].army_ids[0]
    world.armies[army_id].morale = 50
    outcome = BattleSpeechOutcome(morale_delta_percent=10)
    complete_speech(world, "battle_1", outcome)
    assert complete_speech(world, "battle_1", outcome) == []
    assert world.armies[army_id].morale == 60


def test_old_world_document_without_speech_fields_loads_and_omits_them() -> None:
    world, _ = opened_world(speech_ruleset=0)
    document = world.model_dump()
    assert "battle_speech_ruleset" not in document
    assert all("speech" not in battle for battle in document["battles"])
    restored = WorldState.model_validate(document)
    assert restored.battle_speech_ruleset == 0
    assert restored.battles[0].speech is None
