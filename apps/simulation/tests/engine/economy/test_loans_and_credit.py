from app.engine.economy.credit import available_credit, loan_interest_percent
from app.models.world_faction import LoanState

from tests.engine.economy.builders import (
    PLAYER,
    TEST_TUNING,
    events_of,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    run_economy,
)

TUNING = TEST_TUNING


def _loan(principal: int = 100, turns_remaining: int = 12) -> LoanState:
    return LoanState(
        principal=principal, interest_percent=4, turns_remaining=turns_remaining
    )


def _world(treasury: int = 500, wealth: int = 100, loans=(), **faction_overrides):
    regions = [make_region("home", PLAYER, wealth=wealth)] if wealth else []
    faction = make_faction(
        PLAYER, treasury=treasury, loans=list(loans), **faction_overrides
    )
    return make_world(regions=regions, factions=[faction])


def test_credit_limit_is_a_number_of_turns_of_income_minus_debt() -> None:
    world = _world(loans=[_loan(300)])
    assert available_credit(world, TUNING, PLAYER) == 700


def test_each_strike_shrinks_the_limit_and_raises_the_rate() -> None:
    world = _world(credit_strikes=1)
    assert available_credit(world, TUNING, PLAYER) == 500
    assert loan_interest_percent(TUNING, world.factions[PLAYER]) == 6


def test_enough_strikes_close_the_credit_market() -> None:
    world = _world(credit_strikes=TUNING.loan_refused_strikes)
    assert available_credit(world, TUNING, PLAYER) == 0


def test_interest_is_paid_from_the_treasury_each_turn() -> None:
    result = run_economy(_world(treasury=0, loans=[_loan(100)]))
    [event] = events_of(result, "loan_interest_paid")
    assert event.cause.inputs == {
        "interest_due": 4,
        "interest_paid": 4,
        "capitalized": 0,
    }


def test_interest_the_treasury_cannot_cover_is_added_to_the_debt() -> None:
    world = _world(treasury=0, wealth=0, loans=[_loan(100)])
    result = run_economy(world)
    [event] = events_of(result, "loan_interest_paid")
    assert result.world.factions[PLAYER].loans[0].principal == 104
    assert event.cause.inputs["capitalized"] == 4
    assert event.changes == []


def test_installments_come_only_from_the_turns_surplus() -> None:
    result = run_economy(_world(treasury=0, loans=[_loan(100)]))
    [event] = events_of(result, "loan_repaid")
    assert result.world.factions[PLAYER].loans[0].principal == 80
    assert event.cause.inputs["principal_paid"] == 20


def test_a_stockpile_does_not_repay_debt_without_income() -> None:
    world = _world(treasury=1000, wealth=0, loans=[_loan(100)])
    result = run_economy(world)
    assert events_of(result, "loan_repaid") == []
    assert result.world.factions[PLAYER].treasury == 996


def test_a_paid_off_loan_disappears() -> None:
    result = run_economy(_world(loans=[_loan(1)]))
    assert result.world.factions[PLAYER].loans == []


def test_a_loan_that_runs_out_of_term_unpaid_goes_overdue() -> None:
    world = _world(treasury=500, wealth=0, loans=[_loan(100, turns_remaining=1)])
    result = run_economy(world)
    faction = result.world.factions[PLAYER]
    [event] = events_of(result, "loan_overdue")
    assert faction.loans[0].interest_percent == 6
    assert faction.loans[0].turns_remaining == TUNING.loan_term_turns
    assert faction.credit_strikes == 1
    assert faction.reputation == -TUNING.default_reputation_penalty
    assert event.cause.inputs["principal"] == 100


def test_a_loan_taken_this_turn_pays_no_interest_and_does_not_age() -> None:
    from app.models.orders import TakeLoanOrder

    from tests.engine.economy.builders import queued

    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=100))
    result = run_economy(_world(treasury=0), orders=[order])
    [loan] = result.world.factions[PLAYER].loans
    assert (loan.principal, loan.turns_remaining) == (100, TUNING.loan_term_turns)
    assert events_of(result, "loan_interest_paid") == []


def test_clean_turns_slowly_rebuild_credit() -> None:
    world = _world(credit_strikes=2, turns_since_default=5)
    result = run_economy(world)
    faction = result.world.factions[PLAYER]
    assert (faction.credit_strikes, faction.turns_since_default) == (1, 0)
    assert len(events_of(result, "credit_recovered")) == 1


def test_a_clean_turn_before_the_recovery_window_only_counts() -> None:
    result = run_economy(_world(credit_strikes=2, turns_since_default=1))
    faction = result.world.factions[PLAYER]
    assert (faction.credit_strikes, faction.turns_since_default) == (2, 2)


def test_recovery_window_is_tunable() -> None:
    scenario = make_scenario(credit_recovery_turns=1)
    result = run_economy(_world(credit_strikes=1), scenario)
    assert result.world.factions[PLAYER].credit_strikes == 0
