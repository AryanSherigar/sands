from app.engine.ai import rescoring
from app.engine.ai.candidates import Candidate, ScoredCandidate
from app.engine.ai.rescoring import rescore
from app.engine.logistics.supply import SupplyAssessment
from app.models.orders import AttackOrder, MoveArmyOrder, SetTaxRateOrder
from strategy_contracts.battle import SupplyState
from strategy_contracts.enums import TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, SCENARIO, make_world

TUNING = SCENARIO.tuning.ai
SCORE = 20


def _scored(order) -> ScoredCandidate:
    candidate = Candidate(order, ScoreCategory.ATTACK)
    return ScoredCandidate(candidate, SCORE, SCORE, 0)


def _move(region: str) -> ScoredCandidate:
    return _scored(
        MoveArmyOrder(
            faction_id=CAUTIOUS_RIVAL, army_id="army_carrow_1", to_region_id=region
        )
    )


def _attack(region: str) -> ScoredCandidate:
    return _scored(
        AttackOrder(
            faction_id=CAUTIOUS_RIVAL, army_id="army_carrow_1", target_region_id=region
        )
    )


def _rescore(monkeypatch, scored):
    states = {
        "ashford": SupplyState.SUPPLIED,
        "elmstead": SupplyState.STRAINED,
        "fenwatch": SupplyState.ISOLATED,
    }
    monkeypatch.setattr(
        rescoring,
        "supply_assessments",
        lambda world, scenario: {
            (CAUTIOUS_RIVAL, region): SupplyAssessment(state, 0, 0)
            for region, state in states.items()
        },
    )
    return rescore(make_world(), SCENARIO, CAUTIOUS_RIVAL, scored)


def test_supplied_destinations_keep_their_score(monkeypatch) -> None:
    result = _rescore(monkeypatch, [_move("ashford")])

    assert (result[0].score, result[0].adjustment) == (SCORE, 0)


def test_strained_and_isolated_destinations_lose_points(monkeypatch) -> None:
    result = _rescore(monkeypatch, [_move("elmstead"), _attack("fenwatch")])

    assert [item.adjustment for item in result] == [
        -TUNING.supply_strained_penalty,
        -TUNING.supply_isolated_penalty,
    ]
    assert [item.score for item in result] == [
        SCORE - TUNING.supply_strained_penalty,
        SCORE - TUNING.supply_isolated_penalty,
    ]


def test_rescoring_never_removes_candidates_or_touches_other_orders(
    monkeypatch,
) -> None:
    tax = _scored(SetTaxRateOrder(faction_id=CAUTIOUS_RIVAL, tax_rate=TaxRate.HIGH))
    candidates = [_move("fenwatch"), tax]

    result = _rescore(monkeypatch, candidates)

    assert len(result) == len(candidates)
    assert result[1] == tax


def test_unassessed_destinations_are_left_alone(monkeypatch) -> None:
    result = _rescore(monkeypatch, [_move("kings_ford")])

    assert result[0].adjustment == 0
