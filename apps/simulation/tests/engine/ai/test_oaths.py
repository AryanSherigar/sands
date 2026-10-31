from app.engine.ai.oaths import oath_penalty
from app.engine.promises.signing import sign_sworn_promise
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

PENALTY = 25
THRESHOLD = 3


def _scenario():
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.ai.oath_break_penalty = PENALTY
    scenario.tuning.ai.oath_honor_threshold = THRESHOLD
    return scenario


def _world(traits: list[str]):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, traits)
    term = SwornPromiseTerm(
        promisor_id=CAUTIOUS_RIVAL,
        beneficiary_id=PLAYER,
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=5,
    )
    sign_sworn_promise(world, term, None)
    return world


def test_no_promise_gives_zero_penalty() -> None:
    world = make_world()

    assert oath_penalty(world, _scenario(), CAUTIOUS_RIVAL, PLAYER) == 0


def test_promise_to_someone_else_gives_zero_penalty() -> None:
    world = _world([])

    assert oath_penalty(world, _scenario(), CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == 0


def test_honorable_leader_is_forbidden() -> None:
    world = _world(["honorable"])

    assert oath_penalty(world, _scenario(), CAUTIOUS_RIVAL, PLAYER) is None


def test_leader_without_enough_honor_pays_the_penalty() -> None:
    world = _world(["treacherous"])

    assert oath_penalty(world, _scenario(), CAUTIOUS_RIVAL, PLAYER) == PENALTY


def test_threshold_is_inclusive() -> None:
    scenario = _scenario()
    scenario.tuning.ai.oath_honor_threshold = 3
    world = _world(["honorable"])

    assert oath_penalty(world, scenario, CAUTIOUS_RIVAL, PLAYER) is None


def test_breached_or_fulfilled_promise_is_ignored() -> None:
    for status in (CommitmentStatus.BREACHED, CommitmentStatus.FULFILLED):
        world = _world(["honorable"])
        world.commitments[0].status = status

        assert oath_penalty(world, _scenario(), CAUTIOUS_RIVAL, PLAYER) == 0
