from app.engine.ai.candidates import Candidate, ScoredCandidate
from app.engine.ai.selection import select_orders
from app.engine.rng import DeterministicRng
from app.models.orders import SetPayOrder, SetTaxRateOrder
from strategy_contracts.ai import AiTuning
from strategy_contracts.enums import OrderKind, PayLevel, TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, SCENARIO, make_world

PAY_COST = 2
TUNING = AiTuning()
SEEDS = range(200)

SCENARIO_WITH_COSTS = SCENARIO.model_copy(deep=True)
SCENARIO_WITH_COSTS.tuning.order_costs[OrderKind.SET_PAY] = PAY_COST
SCENARIO_WITH_COSTS.tuning.order_costs[OrderKind.SET_TAX_RATE] = PAY_COST


def _pay(index: int, score: int) -> ScoredCandidate:
    order = SetPayOrder(
        faction_id=CAUTIOUS_RIVAL, army_id=f"army_{index}", pay_level=PayLevel.FULL
    )
    candidate = Candidate(order=order, category=ScoreCategory.BUILD)
    return ScoredCandidate(candidate, score, score, 0)


def _tax(rate: TaxRate, score: int) -> ScoredCandidate:
    order = SetTaxRateOrder(faction_id=CAUTIOUS_RIVAL, tax_rate=rate)
    candidate = Candidate(order=order, category=ScoreCategory.HOARD)
    return ScoredCandidate(candidate, score, score, 0)


def _select(scored, budget, seed=1, tuning=TUNING):
    return select_orders(
        scored,
        budget=budget,
        tuning=tuning,
        world=make_world(),
        scenario=SCENARIO_WITH_COSTS,
        rng=DeterministicRng(seed),
    )


def test_zero_budget_selects_nothing() -> None:
    assert _select([_pay(0, 20)], budget=0) == []


def test_never_selects_below_minimum_score() -> None:
    tuning = AiTuning(minimum_score=5)

    assert _select([_pay(0, 4), _pay(1, 3)], budget=10, tuning=tuning) == []


def test_never_selects_outside_variance_margin() -> None:
    scored = [_pay(0, 20), _pay(1, 10)]

    for seed in SEEDS:
        picked = _select(scored, budget=PAY_COST, seed=seed)
        assert [item.score for item in picked] == [20]


def test_clearly_best_always_chosen_with_zero_margin() -> None:
    tuning = AiTuning(variance_margin=0)
    scored = [_pay(0, 20), _pay(1, 19)]

    for seed in SEEDS:
        picked = _select(scored, budget=PAY_COST, seed=seed, tuning=tuning)
        assert [item.score for item in picked] == [20]


def test_total_cost_never_exceeds_budget() -> None:
    scored = [_pay(index, 20) for index in range(5)]

    picked = _select(scored, budget=PAY_COST * 2 + 1)

    assert len(picked) == 2


def test_one_order_per_command_slot() -> None:
    scored = [_tax(TaxRate.HIGH, 20), _tax(TaxRate.LOW, 20)]

    picked = _select(scored, budget=PAY_COST * 4)

    assert len(picked) == 1


def test_same_rng_same_choice() -> None:
    scored = [_pay(0, 20), _pay(1, 19), _pay(2, 18)]

    first = _select(scored, budget=PAY_COST, seed=7)
    second = _select(scored, budget=PAY_COST, seed=7)

    assert first == second


def test_different_seeds_can_choose_different_near_ties() -> None:
    scored = [_pay(0, 20), _pay(1, 19)]

    chosen = {_select(scored, budget=PAY_COST, seed=seed)[0].score for seed in SEEDS}

    assert chosen == {20, 19}


def test_unaffordable_best_does_not_block_cheaper_picks() -> None:
    scenario = SCENARIO_WITH_COSTS.model_copy(deep=True)
    scenario.tuning.order_costs[OrderKind.SET_TAX_RATE] = 5
    scored = [_tax(TaxRate.HIGH, 30), _pay(0, 20)]

    picked = select_orders(
        scored,
        budget=PAY_COST,
        tuning=TUNING,
        world=make_world(),
        scenario=scenario,
        rng=DeterministicRng(1),
    )

    assert [item.score for item in picked] == [20]
