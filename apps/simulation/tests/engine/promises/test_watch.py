from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.prisoners import execute_prisoner
from app.engine.promises.signing import sign_sworn_promise
from app.engine.promises.watch import SWORN_PROMISE_BROKEN, scan_sworn_promises
from app.models.world_diplomacy import CommitmentStatus, PrisonerKind, PrisonerState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.diplomacy
PHASE = PhaseName.DIPLOMACY


def _promise(
    world: WorldState, promise: PromiseKind = PromiseKind.NEVER_ATTACK_FACTION, **extra
) -> SwornPromiseTerm:
    term = SwornPromiseTerm(
        promisor_id=WRATHFUL_RIVAL,
        beneficiary_id=PLAYER,
        promise=promise,
        duration_turns=5,
        **extra,
    )
    sign_sworn_promise(world, term, None)
    return term


def _war() -> EventLogEntry:
    return diplomacy_event("war_declared", ["war_1", WRATHFUL_RIVAL, PLAYER])


def _scan(world: WorldState, events: list[EventLogEntry]) -> list[EventLogEntry]:
    return scan_sworn_promises(world, SCENARIO, events, PHASE)


def test_war_by_promisor_breaches_never_attack() -> None:
    world = make_world()
    _promise(world)

    broken = _scan(world, [_war()])

    assert world.commitments[0].status is CommitmentStatus.BREACHED
    assert [(event.kind, event.is_major, event.phase) for event in broken] == [
        (SWORN_PROMISE_BROKEN, True, PHASE)
    ]
    assert broken[0].cause.subject_ids == [WRATHFUL_RIVAL, PLAYER, "commitment_1"]


def test_breach_charges_standing_marks_oathbreaker_and_grants_ground() -> None:
    world = make_world()
    _promise(world)
    before = world.factions[WRATHFUL_RIVAL].model_copy(deep=True)

    _scan(world, [_war()])

    after = world.factions[WRATHFUL_RIVAL]
    assert after.reputation == before.reputation - TUNING.breach_reputation_cost
    assert after.stability == before.stability - TUNING.breach_stability_cost
    assert [mark.faction_id for mark in world.oathbreakers] == [WRATHFUL_RIVAL]
    ground = world.grounds[0]
    assert (ground.kind, ground.holder_faction_id) == (
        GroundKind.BROKEN_PROMISE,
        PLAYER,
    )
    assert ground.target_faction_id == WRATHFUL_RIVAL


def test_second_scan_does_not_breach_again() -> None:
    world = make_world()
    _promise(world)
    _scan(world, [_war()])
    reputation = world.factions[WRATHFUL_RIVAL].reputation

    assert _scan(world, [_war()]) == []
    assert world.factions[WRATHFUL_RIVAL].reputation == reputation
    assert len(world.grounds) == 1


def test_unrelated_events_leave_the_promise_active() -> None:
    world = make_world()
    _promise(world)

    events = [diplomacy_event("war_declared", ["war_2", PLAYER, WRATHFUL_RIVAL])]

    assert _scan(world, events) == []
    assert world.commitments[0].status is CommitmentStatus.ACTIVE


def test_promise_past_end_turn_is_fulfilled_without_breach() -> None:
    world = make_world()
    world.clock.turn = 2
    _promise(world)
    world.clock.turn = 8

    assert _scan(world, []) == []
    assert world.commitments[0].status is CommitmentStatus.FULFILLED
    assert world.oathbreakers == []


def test_promise_on_its_last_turn_is_still_active() -> None:
    world = make_world()
    world.clock.turn = 2
    _promise(world)
    world.clock.turn = 7

    _scan(world, [])

    assert world.commitments[0].status is CommitmentStatus.ACTIVE


def test_destroyed_party_expires_the_promise() -> None:
    world = make_world()
    _promise(world)
    world.factions[PLAYER].is_destroyed = True

    _scan(world, [_war()])

    assert world.commitments[0].status is CommitmentStatus.EXPIRED
    assert world.oathbreakers == []


def test_each_promise_breaks_independently() -> None:
    world = make_world()
    _promise(world)
    _promise(world, PromiseKind.NEVER_ALLY_WITH, subject_id=CAUTIOUS_RIVAL)

    broken = _scan(world, [_war()])

    statuses = [commitment.status for commitment in world.commitments]
    assert statuses == [CommitmentStatus.BREACHED, CommitmentStatus.ACTIVE]
    assert len(broken) == 1
    assert len(world.oathbreakers) == 1


def test_execution_of_a_beneficiary_prisoner_breaks_spare_prisoners() -> None:
    world = make_world()
    _promise(world, PromiseKind.SPARE_PRISONERS)
    prisoner = PrisonerState(
        id="prisoner_1",
        held_by_id=WRATHFUL_RIVAL,
        origin_faction_id=PLAYER,
        kind=PrisonerKind.CHARACTER,
        character_id="captain",
    )
    world.prisoners.append(prisoner)

    executed = execute_prisoner(world, SCENARIO.tuning.peace, prisoner)
    broken = _scan(world, executed)

    assert [event.kind for event in broken] == [SWORN_PROMISE_BROKEN]
    assert world.commitments[0].status is CommitmentStatus.BREACHED
