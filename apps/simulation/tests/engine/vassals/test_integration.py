from app.engine.ai.standing import is_bound
from app.engine.peace.breach import interaction_relief
from app.engine.pressure.hope import derive_hope
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_diplomacy import CommitmentStatus, TruceState, WarSide, WarState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.peace import PeaceTier
from strategy_contracts.pressure import HopeSource

from tests.engine.alliances.builders import add_alliance
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    add_war,
    make_world,
    set_war_relation,
)

PRESSURE = SCENARIO.tuning.pressure
PEACE = SCENARIO.tuning.peace


def _war_with_vassal() -> tuple[WorldState, WarState]:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    war = add_war(world)
    war.participant_ids.append(CAUTIOUS_RIVAL)
    war.side_by_faction = {
        WRATHFUL_RIVAL: WarSide.ATTACKER,
        PLAYER: WarSide.DEFENDER,
        CAUTIOUS_RIVAL: WarSide.DEFENDER,
    }
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.morale = 0
    return world, war


def _ready(world: WorldState, owner_id: str) -> list[str]:
    ids = []
    for army_id, army in world.armies.items():
        if army.owner_id == owner_id:
            army.morale = PRESSURE.relief_army_min_morale
            ids.append(army_id)
    return ids


def test_vassal_army_on_overlords_side_is_a_hope_source() -> None:
    world, war = _war_with_vassal()
    _ready(world, CAUTIOUS_RIVAL)

    assert HopeSource.ALLIED_ARMY in derive_hope(world, SCENARIO, PLAYER, war).sources


def test_overlord_army_gives_the_vassal_hope() -> None:
    world, war = _war_with_vassal()
    for army in world.armies.values():
        if army.owner_id == CAUTIOUS_RIVAL:
            army.morale = 0
    _ready(world, PLAYER)

    assert (
        HopeSource.ALLIED_ARMY
        in derive_hope(world, SCENARIO, CAUTIOUS_RIVAL, war).sources
    )


def test_vassal_army_in_battle_is_not() -> None:
    world, war = _war_with_vassal()
    ids = _ready(world, CAUTIOUS_RIVAL)
    world.battles.append(
        BattleState(
            id="battle_1",
            region_id="brennmoor",
            attacker_army_ids=ids,
            defender_army_ids=[],
            status=BattleStatus.AWAITING_COMMANDS,
        )
    )

    assert (
        HopeSource.ALLIED_ARMY not in derive_hope(world, SCENARIO, PLAYER, war).sources
    )


def test_vassalage_between_truce_signatories_gives_breach_relief() -> None:
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
    add_vassalage(world, PLAYER, WRATHFUL_RIVAL)

    assert interaction_relief(world, SCENARIO, truce) - before == (
        PEACE.interaction_alliance_relief
    )


def test_is_bound_true_for_active_vassalage() -> None:
    world = make_world()
    assert not is_bound(world, PLAYER, CAUTIOUS_RIVAL)

    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)

    assert is_bound(world, PLAYER, CAUTIOUS_RIVAL)


def test_is_bound_false_after_alliance_commitment_expires_even_if_relation_lingers() -> (
    None
):
    world = make_world()
    alliance = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    assert is_bound(world, PLAYER, CAUTIOUS_RIVAL)
    alliance.status = CommitmentStatus.EXPIRED
    for relation in world.relations:
        relation.status = RelationStatus.ALLIANCE

    assert not is_bound(world, PLAYER, CAUTIOUS_RIVAL)


def test_is_bound_is_not_set_by_war_relations() -> None:
    world = make_world()
    set_war_relation(world, PLAYER, CAUTIOUS_RIVAL)

    assert not is_bound(world, PLAYER, CAUTIOUS_RIVAL)
