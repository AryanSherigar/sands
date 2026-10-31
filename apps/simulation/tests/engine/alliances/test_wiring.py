from app.engine.peace.breach import interaction_relief
from app.engine.pressure.hope import derive_hope
from app.engine.pressure.shocks import record_shock
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_diplomacy import TruceState, WarSide, WarState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.peace import PeaceTier
from strategy_contracts.pressure import HopeSource, ShockKind

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    add_war,
    make_world,
)

PRESSURE = SCENARIO.tuning.pressure
PEACE = SCENARIO.tuning.peace


def _war_with_ally(
    ally_side: WarSide = WarSide.DEFENDER,
) -> tuple[WorldState, WarState]:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    war = add_war(world)
    war.participant_ids.append(CAUTIOUS_RIVAL)
    war.side_by_faction = {
        WRATHFUL_RIVAL: WarSide.ATTACKER,
        PLAYER: WarSide.DEFENDER,
        CAUTIOUS_RIVAL: ally_side,
    }
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.morale = 0
    return world, war


def _ally_armies(world: WorldState):
    return [a for a in world.armies.values() if a.owner_id == CAUTIOUS_RIVAL]


def test_allied_army_gives_hope_reason() -> None:
    world, war = _war_with_ally()
    for army in _ally_armies(world):
        army.morale = PRESSURE.relief_army_min_morale

    reading = derive_hope(world, SCENARIO, PLAYER, war)

    assert HopeSource.ALLIED_ARMY in reading.sources
    assert all(reason.startswith("allied_army:") for reason in reading.reasons)


def test_allied_army_with_low_morale_or_in_battle_gives_none() -> None:
    world, war = _war_with_ally()
    armies = _ally_armies(world)
    for army in armies:
        army.morale = 0
    weak = derive_hope(world, SCENARIO, PLAYER, war)
    for army in armies:
        army.morale = PRESSURE.relief_army_min_morale
    world.battles.append(
        BattleState(
            id="battle_1",
            region_id="brennmoor",
            attacker_army_ids=[
                army_id for army_id, a in world.armies.items() if a in armies
            ],
            defender_army_ids=[],
            status=BattleStatus.AWAITING_COMMANDS,
        )
    )
    busy = derive_hope(world, SCENARIO, PLAYER, war)

    assert HopeSource.ALLIED_ARMY not in weak.sources
    assert HopeSource.ALLIED_ARMY not in busy.sources


def test_allied_army_on_the_other_side_gives_none() -> None:
    world, war = _war_with_ally(ally_side=WarSide.ATTACKER)
    for army in _ally_armies(world):
        army.morale = PRESSURE.relief_army_min_morale

    assert (
        HopeSource.ALLIED_ARMY not in derive_hope(world, SCENARIO, PLAYER, war).sources
    )


def test_ally_outside_the_war_gives_none() -> None:
    world, war = _war_with_ally()
    war.participant_ids.remove(CAUTIOUS_RIVAL)
    del war.side_by_faction[CAUTIOUS_RIVAL]
    for army in _ally_armies(world):
        army.morale = PRESSURE.relief_army_min_morale

    assert (
        HopeSource.ALLIED_ARMY not in derive_hope(world, SCENARIO, PLAYER, war).sources
    )


def test_new_enemy_shock_still_cancels_allied_hope() -> None:
    world, war = _war_with_ally()
    for army in _ally_armies(world):
        army.morale = PRESSURE.relief_army_min_morale
    record_shock(world, SCENARIO, ShockKind.NEW_ENEMY, PLAYER, war.id)

    assert derive_hope(world, SCENARIO, PLAYER, war).sources == []


def test_active_alliance_lowers_breach_pressure_by_tuned_relief() -> None:
    world = make_world()
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    truce = TruceState(
        id="truce_1",
        faction_a=first,
        faction_b=second,
        expires_turn=99,
        tier=PeaceTier.MEDIUM,
        loser_id=WRATHFUL_RIVAL,
        harshness=80,
    )
    world.truces.append(truce)
    before = interaction_relief(world, SCENARIO, truce)
    add_alliance(world, PLAYER, WRATHFUL_RIVAL)
    for relation in world.relations:
        relation.status = RelationStatus.PEACE

    after = interaction_relief(world, SCENARIO, truce)

    assert after - before == PEACE.interaction_alliance_relief
