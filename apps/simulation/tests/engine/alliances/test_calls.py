from app.engine.alliances.calls import issue_calls
from app.engine.alliances.joining import join_war
from app.engine.diplomacy.war_declaration import declare_war
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import WarSide, WarState
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)

CALL_ANSWER_TURNS = SCENARIO.tuning.alliance.call_answer_turns


def _declare(world: WorldState) -> WarState:
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    return world.wars[-1]


def test_declare_war_issues_defensive_call_to_target_ally() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    war = _declare(world)

    [call] = world.alliance.calls
    assert (call.ally_id, call.caller_id, call.war_id) == (
        CAUTIOUS_RIVAL,
        PLAYER,
        war.id,
    )
    assert call.side is WarSide.DEFENDER
    assert call.is_defensive is True
    assert call.deadline_turn == world.clock.turn + CALL_ANSWER_TURNS


def test_declare_war_issues_offensive_call_to_attacker_ally() -> None:
    world = make_world()
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)

    _declare(world)

    [call] = world.alliance.calls
    assert (call.ally_id, call.side, call.is_defensive) == (
        CAUTIOUS_RIVAL,
        WarSide.ATTACKER,
        False,
    )


def test_defensive_ally_not_called_by_attacker_side() -> None:
    world = make_world()
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.DEFENSIVE)

    _declare(world)

    assert world.alliance.calls == []


def test_offensive_ally_of_the_defender_is_not_called() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)

    _declare(world)

    assert world.alliance.calls == []


def test_ally_already_in_war_is_not_called_again() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    war = _declare(world)
    join_war(world, SCENARIO, world.alliance.calls.pop())

    assert issue_calls(world, SCENARIO, war) == []


def test_pending_call_is_not_issued_twice() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    war = _declare(world)

    assert issue_calls(world, SCENARIO, war) == []
    assert len(world.alliance.calls) == 1


def test_destroyed_or_leaderless_ally_is_not_called() -> None:
    destroyed = make_world()
    add_alliance(destroyed, PLAYER, CAUTIOUS_RIVAL)
    destroyed.factions[CAUTIOUS_RIVAL].is_destroyed = True
    leaderless = make_world()
    add_alliance(leaderless, PLAYER, CAUTIOUS_RIVAL)
    leaderless.factions[CAUTIOUS_RIVAL].leader_id = None

    _declare(destroyed)
    _declare(leaderless)

    assert destroyed.alliance.calls == []
    assert leaderless.alliance.calls == []


def test_ally_of_both_sides_gets_two_calls() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)

    _declare(world)

    sides = sorted(call.side.value for call in world.alliance.calls)
    assert sides == ["attacker", "defender"]
    assert {call.ally_id for call in world.alliance.calls} == {CAUTIOUS_RIVAL}


def test_legacy_ruleset_issues_no_calls_and_no_side_map() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    world.alliance_ruleset = 0

    war = _declare(world)

    assert world.alliance.calls == []
    assert war.side_by_faction == {}
