from app.engine.alliances.joining import join_war
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.pressure.wars import find_war, opposing_ids, side_of, side_score
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import WarGoalState, WarSide
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    add_war,
    make_world,
)

SCORES = (30, 12)


def _war_with_defensive_ally(world):
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    return world.wars[-1]


def test_join_adds_participant_side_and_own_goal() -> None:
    world = make_world()
    war = _war_with_defensive_ally(world)
    war.ground_kind = GroundKind.INSULT
    war.goals = [WarGoalState(faction_id=PLAYER, kind=GroundKind.INSULT)]

    events = join_war(world, SCENARIO, world.alliance.calls[0])

    assert CAUTIOUS_RIVAL in war.participant_ids
    assert war.side_by_faction[CAUTIOUS_RIVAL] is WarSide.DEFENDER
    assert WarGoalState(faction_id=CAUTIOUS_RIVAL, kind=GroundKind.INSULT) in war.goals
    assert [event.kind for event in events if event.kind == "ally_joined"] == [
        "ally_joined"
    ]


def test_join_without_a_ground_adds_no_goal() -> None:
    world = make_world()
    war = _war_with_defensive_ally(world)

    join_war(world, SCENARIO, world.alliance.calls[0])

    assert CAUTIOUS_RIVAL not in {goal.faction_id for goal in war.goals}


def test_join_sets_war_relation_with_the_opposing_side() -> None:
    world = make_world()
    _war_with_defensive_ally(world)

    join_war(world, SCENARIO, world.alliance.calls[0])

    pair = tuple(sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL)))
    status = next(
        item.status
        for item in world.relations
        if (item.faction_a, item.faction_b) == pair
    )
    assert status == RelationStatus.WAR


def test_side_score_for_ally_matches_its_side() -> None:
    world = make_world()
    war = _war_with_defensive_ally(world)
    war.war_score_attacker, war.war_score_defender = SCORES
    join_war(world, SCENARIO, world.alliance.calls[0])

    assert side_score(war, CAUTIOUS_RIVAL) == SCORES[1]
    assert side_score(war, WRATHFUL_RIVAL) == SCORES[0]


def test_find_war_matches_ally_and_enemy() -> None:
    world = make_world()
    war = _war_with_defensive_ally(world)
    join_war(world, SCENARIO, world.alliance.calls[0])

    assert find_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) is war
    assert find_war(world, CAUTIOUS_RIVAL, PLAYER) is None


def test_opposing_ids_lists_the_other_side_sorted() -> None:
    world = make_world()
    war = _war_with_defensive_ally(world)
    join_war(world, SCENARIO, world.alliance.calls[0])

    assert opposing_ids(war, WRATHFUL_RIVAL) == sorted([PLAYER, CAUTIOUS_RIVAL])
    assert opposing_ids(war, PLAYER) == [WRATHFUL_RIVAL]


def test_legacy_war_side_derivation() -> None:
    world = make_world()
    war = add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)

    assert side_of(war, WRATHFUL_RIVAL) is WarSide.ATTACKER
    assert side_of(war, PLAYER) is WarSide.DEFENDER
    assert side_of(war, CAUTIOUS_RIVAL) is None
    assert find_war(world, PLAYER, WRATHFUL_RIVAL) is war
