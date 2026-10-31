import pytest
from app.engine.economy.projection import project_balance
from app.exceptions.world_exceptions import UnknownFactionError
from app.models.orders import (
    DeclareDefaultOrder,
    SetPayOrder,
    SetTaxRateOrder,
    TakeLoanOrder,
)
from app.models.world_faction import LoanState
from strategy_contracts.enums import PayLevel, TaxRate

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    events_of,
    make_army,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    queued,
    run_economy,
)

SCENARIO = make_scenario()


def _world(treasury: int = 300, wealth: int = 100, loans=()):
    return make_world(
        regions=[make_region("home", PLAYER, wealth=wealth)],
        factions=[
            make_faction(PLAYER, treasury=treasury, loans=list(loans)),
            make_faction(RIVAL),
        ],
        armies=[
            make_army("army_a", PLAYER, troops={"infantry": 300}),
            make_army("army_b", PLAYER, troops={"cavalry": 100}),
        ],
    )


def test_a_comfortable_balance_has_no_shortfall() -> None:
    projection = project_balance(_world(), SCENARIO, PLAYER, [])
    assert (projection.income, projection.upkeep) == (100, 50)
    assert projection.balance_after == 350
    assert projection.shortfall == 0
    assert not projection.is_unresolved


def test_the_projection_matches_what_the_phase_then_does() -> None:
    loan = LoanState(principal=200, interest_percent=4, turns_remaining=9)
    world = _world(loans=[loan])
    projection = project_balance(world, SCENARIO, PLAYER, [])
    result = run_economy(world, SCENARIO)
    [income] = events_of(result, "income_collected")
    [interest] = events_of(result, "loan_interest_paid")
    [upkeep] = events_of(result, "upkeep_paid")
    repaid = sum(
        event.cause.inputs["principal_paid"]
        for event in events_of(result, "loan_repaid")
    )
    final = result.world.factions[PLAYER].treasury
    assert projection.income == income.changes[0].after - income.changes[0].before
    assert projection.interest == interest.cause.inputs["interest_paid"]
    assert projection.upkeep == -(upkeep.changes[0].after - upkeep.changes[0].before)
    assert projection.balance_after == final + repaid


def test_a_negative_balance_is_an_unresolved_shortfall() -> None:
    projection = project_balance(_world(treasury=0, wealth=10), SCENARIO, PLAYER, [])
    assert projection.shortfall == 40
    assert projection.is_unresolved
    assert projection.available_credit > 0


def test_queueing_a_loan_resolves_the_shortfall() -> None:
    world = _world(treasury=0, wealth=10)
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=40))
    projection = project_balance(world, SCENARIO, PLAYER, [order])
    assert projection.shortfall == 0
    assert not projection.is_unresolved


def test_queueing_a_default_resolves_the_block_without_removing_the_shortfall() -> None:
    world = _world(treasury=0, wealth=10)
    order = queued(DeclareDefaultOrder(faction_id=PLAYER))
    projection = project_balance(world, SCENARIO, PLAYER, [order])
    assert projection.shortfall == 40
    assert projection.is_default_declared
    assert not projection.is_unresolved


def test_cutting_pay_or_raising_taxes_shrinks_the_shortfall() -> None:
    world = _world(treasury=0, wealth=10)
    base = project_balance(world, SCENARIO, PLAYER, []).shortfall
    cut = queued(
        SetPayOrder(faction_id=PLAYER, army_id="army_a", pay_level=PayLevel.REDUCED),
        "order_1",
    )
    tax = queued(SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.HIGH), "order_2")
    assert project_balance(world, SCENARIO, PLAYER, [cut]).shortfall < base
    assert project_balance(world, SCENARIO, PLAYER, [tax]).shortfall < base


def test_projecting_does_not_change_the_world() -> None:
    world = _world(treasury=0, wealth=10)
    before = world.model_dump_json()
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=40))
    project_balance(world, SCENARIO, PLAYER, [order])
    assert world.model_dump_json() == before


def test_an_unknown_faction_is_an_error() -> None:
    with pytest.raises(UnknownFactionError):
        project_balance(_world(), SCENARIO, "house_zz", [])
