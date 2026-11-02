from app.engine.diplomacy.events import diplomacy_event
from app.engine.promises.matchers import is_breach
from app.models.world_events import EventLogEntry
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

PROMISOR = "house_a"
BENEFICIARY = "house_b"
THIRD = "house_c"


def _term(promise: PromiseKind, subject_id: str | None = None) -> SwornPromiseTerm:
    return SwornPromiseTerm(
        promisor_id=PROMISOR,
        beneficiary_id=BENEFICIARY,
        promise=promise,
        subject_id=subject_id,
        duration_turns=5,
    )


def _event(kind: str, *subject_ids: str) -> EventLogEntry:
    return diplomacy_event(kind, list(subject_ids))


def test_war_by_promisor_on_beneficiary_breaches_never_attack() -> None:
    term = _term(PromiseKind.NEVER_ATTACK_FACTION)

    assert is_breach(term, _event("war_declared", "war_1", PROMISOR, BENEFICIARY))


def test_war_in_the_other_direction_or_on_a_third_party_is_no_breach() -> None:
    term = _term(PromiseKind.NEVER_ATTACK_FACTION)

    assert not is_breach(term, _event("war_declared", "war_1", BENEFICIARY, PROMISOR))
    assert not is_breach(term, _event("war_declared", "war_1", PROMISOR, THIRD))


def test_alliance_with_the_subject_breaches_in_either_order() -> None:
    term = _term(PromiseKind.NEVER_ALLY_WITH, THIRD)

    assert is_breach(term, _event("alliance_signed", PROMISOR, THIRD))
    assert is_breach(term, _event("alliance_signed", THIRD, PROMISOR))


def test_alliance_not_involving_both_promisor_and_subject_is_no_breach() -> None:
    term = _term(PromiseKind.NEVER_ALLY_WITH, THIRD)

    assert not is_breach(term, _event("alliance_signed", BENEFICIARY, THIRD))
    assert not is_breach(term, _event("alliance_signed", PROMISOR, BENEFICIARY))


def test_execution_of_beneficiary_prisoner_by_promisor_breaches_spare() -> None:
    term = _term(PromiseKind.SPARE_PRISONERS)

    assert is_breach(term, _event("prisoner_executed", "p1", PROMISOR, BENEFICIARY))


def test_other_executions_are_no_breach() -> None:
    term = _term(PromiseKind.SPARE_PRISONERS)

    assert not is_breach(term, _event("prisoner_executed", "p1", PROMISOR, THIRD))
    assert not is_breach(term, _event("prisoner_executed", "p1", BENEFICIARY, PROMISOR))


def test_unrelated_event_kinds_never_match() -> None:
    for promise, subject in (
        (PromiseKind.NEVER_ATTACK_FACTION, None),
        (PromiseKind.NEVER_ALLY_WITH, THIRD),
        (PromiseKind.SPARE_PRISONERS, None),
    ):
        event = _event("peace_signed", "war_1", PROMISOR, BENEFICIARY, THIRD)
        assert not is_breach(_term(promise, subject), event)


def test_occupying_the_subject_region_breaches_never_occupy_region() -> None:
    term = _term(PromiseKind.NEVER_OCCUPY_REGION, "reg_gate")

    assert is_breach(term, _event("region_occupied", PROMISOR, "reg_gate"))


def test_occupying_another_region_or_by_another_faction_is_no_breach() -> None:
    term = _term(PromiseKind.NEVER_OCCUPY_REGION, "reg_gate")

    assert not is_breach(term, _event("region_occupied", PROMISOR, "reg_other"))
    assert not is_breach(term, _event("region_occupied", THIRD, "reg_gate"))
    assert not is_breach(term, _event("siege_started", PROMISOR, "reg_gate"))
