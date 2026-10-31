from app.engine.ai.generators.treasury import (
    disband_candidates,
    loan_candidates,
    pay_candidates,
)
from app.models.orders import DisbandArmyOrder, SetPayOrder, TakeLoanOrder
from app.models.world_diplomacy import WarState
from app.models.world_faction import LoanState
from strategy_contracts.enums import PayLevel, TroopType
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai
POOR = TUNING.low_treasury - 1
RICH = TUNING.low_treasury * 2
CARROW_ARMIES = ["army_carrow_1", "army_carrow_2"]


def _world(treasury: int):
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].treasury = treasury
    return world


def test_poor_faction_proposes_a_capped_loan() -> None:
    candidates = loan_candidates(_world(POOR), SCENARIO, CAUTIOUS_RIVAL)

    assert len(candidates) == 1
    order = candidates[0].order
    assert isinstance(order, TakeLoanOrder)
    assert 0 < order.amount <= TUNING.loan_cap
    assert candidates[0].category == ScoreCategory.HOARD
    assert candidates[0].base_score == TUNING.situation_bonus


def test_comfortable_faction_proposes_no_loan() -> None:
    assert loan_candidates(_world(RICH), SCENARIO, CAUTIOUS_RIVAL) == []


def test_loans_disabled_means_no_loan() -> None:
    scenario = SCENARIO.model_copy(deep=True)
    scenario.toggles.is_loans_enabled = False

    assert loan_candidates(_world(POOR), scenario, CAUTIOUS_RIVAL) == []


def test_faction_without_credit_proposes_no_loan() -> None:
    world = _world(POOR)
    world.factions[CAUTIOUS_RIVAL].credit_strikes = 99

    assert loan_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def test_poor_faction_reduces_pay_for_every_army() -> None:
    candidates = pay_candidates(_world(POOR), SCENARIO, CAUTIOUS_RIVAL)

    assert [item.order.army_id for item in candidates] == CARROW_ARMIES
    assert {item.order.pay_level for item in candidates} == {PayLevel.REDUCED}
    assert {item.category for item in candidates} == {ScoreCategory.HOARD}


def test_rich_faction_restores_reduced_pay() -> None:
    world = _world(RICH)
    world.armies["army_carrow_1"].pay_level = PayLevel.REDUCED

    candidates = pay_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert len(candidates) == 1
    assert isinstance(candidates[0].order, SetPayOrder)
    assert candidates[0].order.pay_level == PayLevel.FULL
    assert candidates[0].category == ScoreCategory.BUILD


def test_middling_treasury_leaves_pay_alone() -> None:
    assert pay_candidates(_world(TUNING.low_treasury), SCENARIO, CAUTIOUS_RIVAL) == []


def test_poor_peaceful_faction_may_disband_a_small_army() -> None:
    world = _world(POOR)
    world.armies["army_carrow_2"].troops = {
        TroopType.INFANTRY: TUNING.disband_below_troops
    }

    candidates = disband_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert [item.order for item in candidates] == [
        DisbandArmyOrder(faction_id=CAUTIOUS_RIVAL, army_id="army_carrow_2")
    ]
    assert candidates[0].category == ScoreCategory.HOARD


def test_faction_at_war_never_disbands() -> None:
    world = _world(POOR)
    world.armies["army_carrow_2"].troops = {TroopType.INFANTRY: 1}
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=CAUTIOUS_RIVAL,
            started_turn=0,
        )
    )

    assert disband_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def test_rich_faction_never_disbands() -> None:
    world = _world(RICH)
    world.armies["army_carrow_2"].troops = {TroopType.INFANTRY: 1}

    assert disband_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def test_a_faction_already_deep_in_debt_borrows_no_more() -> None:
    world = _world(POOR)
    world.factions[CAUTIOUS_RIVAL].loans.append(
        LoanState(principal=TUNING.loan_cap, interest_percent=5, turns_remaining=10)
    )

    assert loan_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []
