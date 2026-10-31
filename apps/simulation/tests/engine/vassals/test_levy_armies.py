from app.engine.vassals.consequences import apply_reply
from app.models.world_army import ArmyState, MarchState
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_state import WorldState
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_demand,
    make_world,
)

GRANTED = 20
ASKED = 50
EXCESS = ASKED - GRANTED
REGION_MANPOWER = 100
VASSAL_INFANTRY = 100


def _owned(world: WorldState, faction_id: str) -> list[str]:
    return sorted(k for k, r in world.regions.items() if r.owner_id == faction_id)


def _setup() -> tuple[WorldState, object]:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=GRANTED)
    for region in world.regions.values():
        region.manpower = REGION_MANPOWER
    world.armies = {}
    return world, commitment


def _add_army(world: WorldState, army_id: str, owner_id: str, troops: int) -> ArmyState:
    army = ArmyState(
        id=army_id,
        owner_id=owner_id,
        troops={"infantry": troops},
        morale=50,
        location_id=_owned(world, owner_id)[0],
    )
    world.armies[army_id] = army
    return army


def _manpower(world: WorldState, faction_id: str) -> int:
    return sum(r.manpower for r in world.regions.values() if r.owner_id == faction_id)


def _soldiers(world: WorldState, owner_id: str) -> int:
    return sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == owner_id
    )


def _answer(world, commitment, reply: DemandReply, amount: int = ASKED):
    demand = make_demand(commitment, DemandKind.LEVY, amount)
    return apply_reply(world, SCENARIO, demand, reply)


def test_excess_comes_from_armies_not_regions() -> None:
    world, commitment = _setup()
    _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)
    manpower = _manpower(world, CAUTIOUS_RIVAL)

    _answer(world, commitment, DemandReply.ACCEPT)

    assert _manpower(world, CAUTIOUS_RIVAL) == manpower - manpower * GRANTED // 100
    assert world.armies["army_v"].troops["infantry"] == VASSAL_INFANTRY - EXCESS
    assert _soldiers(world, PLAYER) == EXCESS


def test_counter_halves_the_excess() -> None:
    world, commitment = _setup()
    _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)

    _answer(world, commitment, DemandReply.COUNTER)

    assert _soldiers(world, PLAYER) == EXCESS // 2


def test_refusal_takes_nothing() -> None:
    world, commitment = _setup()
    _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)
    manpower = _manpower(world, CAUTIOUS_RIVAL)

    _answer(world, commitment, DemandReply.REFUSE)

    assert _soldiers(world, CAUTIOUS_RIVAL) == VASSAL_INFANTRY
    assert _manpower(world, CAUTIOUS_RIVAL) == manpower


def test_moving_army_is_skipped_and_manpower_covers_the_excess() -> None:
    world, commitment = _setup()
    army = _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)
    destination = _owned(world, CAUTIOUS_RIVAL)[-1]
    army.march = MarchState.model_construct(from_id=army.location_id, to_id=destination)
    manpower = _manpower(world, CAUTIOUS_RIVAL)

    _answer(world, commitment, DemandReply.ACCEPT)

    assert army.troops["infantry"] == VASSAL_INFANTRY
    assert _manpower(world, CAUTIOUS_RIVAL) == manpower - manpower * ASKED // 100


def test_engaged_army_is_skipped() -> None:
    world, commitment = _setup()
    army = _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)
    world.battles.append(
        BattleState.model_construct(
            id="battle_1",
            region_id=army.location_id,
            status=BattleStatus.AWAITING_COMMANDS,
            attacker_army_ids=["army_v"],
            defender_army_ids=[],
        )
    )

    _answer(world, commitment, DemandReply.ACCEPT)

    assert army.troops["infantry"] == VASSAL_INFANTRY


def test_no_armies_falls_back_to_regional_manpower() -> None:
    world, commitment = _setup()
    manpower = _manpower(world, CAUTIOUS_RIVAL)

    _answer(world, commitment, DemandReply.ACCEPT)

    assert _manpower(world, CAUTIOUS_RIVAL) == manpower - manpower * ASKED // 100


def test_rounding_to_zero_soldiers_falls_back() -> None:
    world, commitment = _setup()
    army = _add_army(world, "army_v", CAUTIOUS_RIVAL, 2)
    manpower = _manpower(world, CAUTIOUS_RIVAL)

    _answer(world, commitment, DemandReply.ACCEPT, amount=GRANTED + 10)

    assert army.troops["infantry"] == 2
    assert _manpower(world, CAUTIOUS_RIVAL) < manpower - manpower * GRANTED // 100


def test_transfer_is_deterministic_across_army_order() -> None:
    first, commitment_a = _setup()
    second, commitment_b = _setup()
    for army_id in ("army_a", "army_b"):
        _add_army(first, army_id, CAUTIOUS_RIVAL, VASSAL_INFANTRY)
    for army_id in ("army_b", "army_a"):
        _add_army(second, army_id, CAUTIOUS_RIVAL, VASSAL_INFANTRY)

    _answer(first, commitment_a, DemandReply.ACCEPT)
    _answer(second, commitment_b, DemandReply.ACCEPT)

    assert {k: v.troops for k, v in sorted(first.armies.items())} == {
        k: v.troops for k, v in sorted(second.armies.items())
    }


def test_new_overlord_army_is_created_at_the_capital_when_none_exists() -> None:
    world, commitment = _setup()
    _add_army(world, "army_v", CAUTIOUS_RIVAL, VASSAL_INFANTRY)

    _answer(world, commitment, DemandReply.ACCEPT)

    capital = world.factions[PLAYER].capital_region_id
    overlord_armies = [a for a in world.armies.values() if a.owner_id == PLAYER]
    assert len(overlord_armies) == 1
    assert overlord_armies[0].location_id == capital
