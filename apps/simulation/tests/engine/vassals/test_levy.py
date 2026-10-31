from app.engine.diplomacy.war_declaration import declare_war
from app.engine.pressure.wars import side_of
from app.models.orders import DeclareWarOrder
from app.models.world_alliance import CallKind
from app.models.world_diplomacy import WarSide
from app.models.world_state import WorldState

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)

LEVY_PERCENT = 30
MANPOWER = 100


def _declare(world: WorldState, attacker: str, target: str):
    declare_war(
        world, SCENARIO, DeclareWarOrder(faction_id=attacker, target_faction_id=target)
    )
    return world.wars[-1]


def _vassal_manpower(world: WorldState, vassal_id: str) -> int:
    return sum(
        region.manpower
        for region in world.regions.values()
        if region.owner_id == vassal_id
    )


def test_levy_vassal_joins_overlords_side_without_an_answer() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)

    war = _declare(world, WRATHFUL_RIVAL, PLAYER)

    assert side_of(war, CAUTIOUS_RIVAL) is WarSide.DEFENDER
    assert CAUTIOUS_RIVAL in war.participant_ids
    assert not [c for c in world.alliance.calls if c.kind is CallKind.LEVY]


def test_attacking_overlord_levies_the_vassal_to_the_attacker_side() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)

    war = _declare(world, PLAYER, WRATHFUL_RIVAL)

    assert side_of(war, CAUTIOUS_RIVAL) is WarSide.ATTACKER


def test_vassal_without_a_levy_term_is_not_called() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=0)

    war = _declare(world, WRATHFUL_RIVAL, PLAYER)

    assert side_of(war, CAUTIOUS_RIVAL) is None


def test_levy_moves_the_share_of_manpower_to_the_capital_region() -> None:
    world = make_world()
    for region in world.regions.values():
        region.manpower = MANPOWER
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)
    before_vassal = _vassal_manpower(world, CAUTIOUS_RIVAL)
    before_overlord = _vassal_manpower(world, PLAYER)

    _declare(world, WRATHFUL_RIVAL, PLAYER)

    moved = before_vassal - _vassal_manpower(world, CAUTIOUS_RIVAL)
    assert moved > 0
    assert moved <= before_vassal * LEVY_PERCENT // 100
    assert _vassal_manpower(world, PLAYER) == before_overlord + moved


def test_levy_skips_destroyed_and_leaderless_vassals() -> None:
    destroyed = make_world()
    add_vassalage(destroyed, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)
    destroyed.factions[CAUTIOUS_RIVAL].is_destroyed = True
    leaderless = make_world()
    add_vassalage(leaderless, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)
    leaderless.factions[CAUTIOUS_RIVAL].leader_id = None

    for world in (destroyed, leaderless):
        war = _declare(world, WRATHFUL_RIVAL, PLAYER)
        assert side_of(war, CAUTIOUS_RIVAL) is None


def test_levy_not_issued_against_the_vassals_own_overlord() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, WRATHFUL_RIVAL, levy=LEVY_PERCENT)

    war = _declare(world, WRATHFUL_RIVAL, PLAYER)

    assert side_of(war, WRATHFUL_RIVAL) is WarSide.ATTACKER
    assert war.participant_ids.count(WRATHFUL_RIVAL) == 1


def test_legacy_world_levies_nobody() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=LEVY_PERCENT)
    world.vassal_ruleset = 0

    war = _declare(world, WRATHFUL_RIVAL, PLAYER)

    assert side_of(war, CAUTIOUS_RIVAL) is None
