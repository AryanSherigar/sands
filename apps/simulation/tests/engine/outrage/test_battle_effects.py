from app.engine.battles.policy import fallback_intent
from app.engine.battles.views import intent_briefing
from app.models.battle_command import SurrenderCommand
from app.models.battle_intelligence import IntentKind
from app.models.world_character import CommanderState, CommanderStatus
from app.models.world_diplomacy import OutrageState
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState
from strategy_contracts.enums import TroopType
from strategy_contracts.scene import OutrageLevel

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    command,
    exchange,
    start_battle,
)


def _enrage(world: WorldState, faction_id: str) -> None:
    world.outrage.append(
        OutrageState(
            faction_id=faction_id,
            level=OutrageLevel.ENRAGED,
            expires_turn=world.clock.turn + 5,
        )
    )


def test_a_press_bias_charges_even_when_outnumbered() -> None:
    world, scenario = battle_fixture(1, 1000)
    start_battle(world, scenario)
    world.battles[0].contingents[ATTACKER].supply = SupplyState.SUPPLIED
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    tuning = scenario.tuning.battle

    assert fallback_intent(briefing, tuning) == IntentKind.DELAY
    assert fallback_intent(briefing, tuning, should_press=True) == IntentKind.PRESS


def test_a_press_bias_still_preserves_a_broken_army() -> None:
    world, scenario = battle_fixture(1, 1000)
    start_battle(world, scenario)
    world.armies["army_a"].morale = 10
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)

    result = fallback_intent(briefing, scenario.tuning.battle, should_press=True)

    assert result == IntentKind.PRESERVE


def test_an_enraged_captor_takes_no_prisoners() -> None:
    world, scenario = battle_fixture(100, 100)
    world.armies["army_a"].commander_id = "commander_a"
    world.commanders["commander_a"] = CommanderState(
        id="commander_a", name="A", faction_id=ATTACKER, army_id="army_a"
    )
    _enrage(world, DEFENDER)
    start_battle(world, scenario)

    result = exchange(
        world,
        scenario,
        [command(SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )

    assert result.world.prisoners == []
    assert result.world.commanders["commander_a"].status == CommanderStatus.DEAD
    assert result.receipt.accounting[0].captives == {}
    assert result.receipt.accounting[0].combat_losses == {TroopType.INFANTRY: 100}


def test_troops_facing_no_quarter_fight_with_steadier_morale() -> None:
    calm, scenario = battle_fixture(1000, 1000)
    angry, _ = battle_fixture(1000, 1000)
    _enrage(angry, DEFENDER)
    start_battle(calm, scenario)
    start_battle(angry, scenario)

    steady = exchange(angry, scenario).world.armies["army_a"].morale
    baseline = exchange(calm, scenario).world.armies["army_a"].morale

    assert steady - baseline == scenario.tuning.outrage.no_quarter_morale_bonus
