from app.engine.alliances.answers import apply_answer, npc_answer, resolve_calls
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.pressure.wars import side_of
from app.engine.vassals.registry import vassalage_of
from app.models.orders import AnswerCallOrder, DeclareWarOrder
from app.models.world_alliance import CallKind
from app.models.world_diplomacy import CommitmentStatus, WarSide
from app.models.world_state import WorldState

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)

DIPLOMACY = SCENARIO.tuning.diplomacy


def _attacked_vassal_world() -> WorldState:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    return world


def _oathbreaker_marks(world: WorldState, faction_id: str) -> int:
    return len([m for m in world.oathbreakers if m.faction_id == faction_id])


def test_attack_on_vassal_calls_overlord_as_defensive() -> None:
    world = _attacked_vassal_world()

    [call] = world.alliance.calls

    assert (call.kind, call.caller_id, call.ally_id) == (
        CallKind.PROTECTION,
        CAUTIOUS_RIVAL,
        PLAYER,
    )
    assert call.is_defensive is True
    assert call.side is WarSide.DEFENDER


def test_attack_on_the_overlord_issues_no_protection_call() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    assert not [c for c in world.alliance.calls if c.kind is CallKind.PROTECTION]


def test_overlord_joining_enters_the_war_on_the_vassals_side() -> None:
    world = _attacked_vassal_world()
    [call] = world.alliance.calls

    apply_answer(
        world,
        SCENARIO,
        AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True),
    )

    assert side_of(world.wars[-1], PLAYER) is WarSide.DEFENDER
    assert vassalage_of(world, CAUTIOUS_RIVAL) is not None


def test_npc_overlord_answer_matches_its_join_score() -> None:
    world = make_world()
    world.factions[PLAYER].is_player = False
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    [call] = world.alliance.calls
    expected = npc_answer(world, SCENARIO, call).is_joining

    world.clock.turn = call.deadline_turn
    resolve_calls(world, SCENARIO)

    assert (side_of(world.wars[-1], PLAYER) is not None) is expected


def test_refused_protection_call_frees_the_vassal_and_charges_breach_once() -> None:
    world = _attacked_vassal_world()
    [call] = world.alliance.calls
    reputation = world.factions[PLAYER].reputation

    apply_answer(
        world,
        SCENARIO,
        AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=False),
    )

    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert world.commitments[-1].status is CommitmentStatus.BREACHED
    assert _oathbreaker_marks(world, PLAYER) == 1
    assert world.factions[PLAYER].reputation == reputation - (
        DIPLOMACY.breach_reputation_cost
    )


def test_unanswered_player_overlord_protection_call_is_a_refusal() -> None:
    world = _attacked_vassal_world()
    [call] = world.alliance.calls
    world.clock.turn = call.deadline_turn

    resolve_calls(world, SCENARIO)

    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert _oathbreaker_marks(world, PLAYER) == 1
