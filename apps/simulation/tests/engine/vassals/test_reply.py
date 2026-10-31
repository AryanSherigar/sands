from app.engine.vassals.reply import choose_reply, pick_best
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_demand,
    make_world,
    set_axes,
    set_power,
    set_unrest,
)

EVEN = 1000
WEAK = 300


def _scene(axes, vassal_troops, unrest, asked=30, tribute=20):
    world = make_world()
    scenario = set_axes(world, SCENARIO, CAUTIOUS_RIVAL, **axes)
    set_power(world, CAUTIOUS_RIVAL, PLAYER, vassal_troops, EVEN)
    set_unrest(world, CAUTIOUS_RIVAL, unrest)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=tribute)
    demand = make_demand(commitment, DemandKind.TRIBUTE, asked)
    return world, scenario, demand


def test_proud_aggressive_strong_unrestful_vassal_rebels() -> None:
    world, scenario, demand = _scene({"pride": 3, "aggression": 3}, EVEN, 60, asked=80)

    assert choose_reply(world, scenario, demand).reply is DemandReply.REBEL


def test_weak_vassal_never_rebels_however_unrestful() -> None:
    world, scenario, demand = _scene({"pride": 3, "aggression": 3}, 100, 100, asked=100)

    assert choose_reply(world, scenario, demand).reply is not DemandReply.REBEL


def test_pliant_weak_vassal_accepts_a_moderate_excess() -> None:
    world, scenario, demand = _scene({"honor": 3, "trust": 3}, WEAK, 10)

    assert choose_reply(world, scenario, demand).reply is DemandReply.ACCEPT


def test_cunning_vassal_counters_a_mid_excess() -> None:
    world, scenario, demand = _scene({"cunning": 3, "pride": 3}, EVEN, 10)

    assert choose_reply(world, scenario, demand).reply is DemandReply.COUNTER


def test_extreme_excess_with_pride_refuses_strongly() -> None:
    world, scenario, demand = _scene({"pride": 3, "aggression": 3}, EVEN, 10, asked=80)

    assert choose_reply(world, scenario, demand).reply is DemandReply.REFUSE_STRONGLY


def test_mild_excess_with_pride_refuses_plainly() -> None:
    world, scenario, demand = _scene({"pride": 3, "aggression": 3}, EVEN, 10, asked=24)

    assert choose_reply(world, scenario, demand).reply is DemandReply.REFUSE


def test_same_inputs_give_the_same_reply_and_reason() -> None:
    world, scenario, demand = _scene({"pride": 2}, EVEN, 30)

    assert choose_reply(world, scenario, demand) == choose_reply(
        world, scenario, demand
    )
    assert choose_reply(world, scenario, demand).reason_key


def test_tie_breaks_in_fixed_order() -> None:
    scores = {
        DemandReply.REBEL: 5,
        DemandReply.REFUSE_STRONGLY: 5,
        DemandReply.COUNTER: 5,
        DemandReply.ACCEPT: 5,
    }

    assert pick_best(scores) is DemandReply.ACCEPT
    del scores[DemandReply.ACCEPT]
    assert pick_best(scores) is DemandReply.COUNTER
