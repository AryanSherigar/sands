import pytest
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.outrage.mobilize import validate_mobilize
from app.engine.outrage.status import is_mobilized
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import MobilizeOrder
from app.models.world_diplomacy import OutrageState
from strategy_contracts.enums import OrderKind
from strategy_contracts.scene import OutrageLevel

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.outrage.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
)
from tests.engine.pressure.builders import add_war

ORDER = MobilizeOrder(faction_id=PLAYER)


def _at_war():
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    return world


def test_mobilize_costs_a_heavy_order_by_default() -> None:
    assert SCENARIO.tuning.order_costs[OrderKind.MOBILIZE] == 2


def test_mobilizing_marks_the_faction_mobilized_for_the_configured_turns() -> None:
    world = queue_npc_order(_at_war(), SCENARIO, ORDER)

    result = run_phase(DiplomacyPhase(), world)

    assert is_mobilized(result.world, PLAYER)
    state = next(item for item in result.world.outrage if item.faction_id == PLAYER)
    turns = SCENARIO.tuning.outrage.mobilization_turns
    assert state.mobilized_until_turn == world.clock.turn + turns
    assert "mobilization_ordered" in [event.kind for event in result.events]


def test_mobilizing_does_not_change_an_existing_outrage_level() -> None:
    world = _at_war()
    enrage(world, faction_id=PLAYER, offender_id=WRATHFUL_RIVAL)
    state = next(item for item in world.outrage if item.faction_id == PLAYER)
    before = state.level
    state.mobilized_until_turn = 0
    world = queue_npc_order(world, SCENARIO, ORDER)

    result = run_phase(DiplomacyPhase(), world)

    state = next(item for item in result.world.outrage if item.faction_id == PLAYER)
    assert state.level == before
    assert is_mobilized(result.world, PLAYER)


@pytest.mark.parametrize(
    ("reason", "setup"),
    [
        ("not_at_war", lambda world: world.wars.clear()),
        ("outrage_disabled", lambda world: setattr(world, "outrage_ruleset", 0)),
        (
            "already_mobilized",
            lambda world: world.outrage.append(
                OutrageState(
                    faction_id=PLAYER,
                    level=OutrageLevel.NONE,
                    expires_turn=0,
                    mobilized_until_turn=world.clock.turn + 3,
                )
            ),
        ),
    ],
)
def test_invalid_mobilization_is_rejected(reason, setup) -> None:
    world = _at_war()
    setup(world)

    with pytest.raises(CommandError) as error:
        validate_mobilize(world, SCENARIO, ORDER)

    assert error.value.code == reason


def test_an_order_that_goes_stale_fails_and_is_refunded() -> None:
    world = queue_npc_order(_at_war(), SCENARIO, ORDER)
    budget = world.factions[PLAYER].orders_remaining
    world.wars.clear()

    result = run_phase(DiplomacyPhase(), world)

    command = result.world.accepted_commands[-1]
    assert command.status == CommandStatus.FAILED
    assert command.failure_reason == "not_at_war"
    assert (
        result.world.factions[PLAYER].orders_remaining
        == budget + SCENARIO.tuning.order_costs[OrderKind.MOBILIZE]
    )
    assert not is_mobilized(result.world, PLAYER)
