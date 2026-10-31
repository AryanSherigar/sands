from app.engine.alliances.joining import join_war
from app.engine.alliances.registry import alliance_between
from app.engine.diplomacy.war_declaration import declare_war
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)

DIPLOMACY = SCENARIO.tuning.diplomacy


def _reputation_after_declaring_on_player(has_alliance: bool) -> tuple[int, WorldState]:
    world = make_world()
    if has_alliance:
        add_alliance(world, WRATHFUL_RIVAL, PLAYER)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    return world.factions[WRATHFUL_RIVAL].reputation, world


def test_declaring_war_on_an_ally_breaches_the_alliance_once() -> None:
    allied_reputation, world = _reputation_after_declaring_on_player(True)
    plain_reputation, _ = _reputation_after_declaring_on_player(False)

    assert world.commitments[0].status is CommitmentStatus.BREACHED
    assert alliance_between(world, WRATHFUL_RIVAL, PLAYER) is None
    assert plain_reputation - allied_reputation == DIPLOMACY.breach_reputation_cost
    assert len(world.oathbreakers) == 1


def test_joining_against_an_own_ally_ends_that_alliance_without_breach_cost() -> None:
    world: WorldState = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    side_tie = add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    defender_call = next(
        call for call in world.alliance.calls if call.caller_id == PLAYER
    )
    join_war(world, SCENARIO, defender_call)

    assert side_tie.status is CommitmentStatus.EXPIRED
    assert world.oathbreakers == []
