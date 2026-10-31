from app.engine.ai import catalog
from app.engine.ai.candidates import Candidate
from app.models.orders import SetTaxRateOrder
from strategy_contracts.enums import TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, SCENARIO, make_world


def _candidate(rate: TaxRate, category: ScoreCategory) -> Candidate:
    order = SetTaxRateOrder(faction_id=CAUTIOUS_RIVAL, tax_rate=rate)
    return Candidate(order=order, category=category)


def test_generate_candidates_uses_registry_order(monkeypatch) -> None:
    first = [_candidate(TaxRate.LOW, ScoreCategory.BUILD)]
    second = [_candidate(TaxRate.HIGH, ScoreCategory.HOARD)]
    monkeypatch.setattr(
        catalog,
        "GENERATORS",
        (lambda *_: first, lambda *_: second),
    )

    result = catalog.generate_candidates(make_world(), SCENARIO, CAUTIOUS_RIVAL)

    assert result == first + second


def test_legal_candidates_keeps_orders_the_validator_accepts() -> None:
    world = make_world()
    candidates = [_candidate(TaxRate.HIGH, ScoreCategory.HOARD)]

    kept = catalog.legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates)

    assert kept == candidates


def test_legal_candidates_drops_orders_the_validator_rejects() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].orders_remaining = 0
    candidates = [_candidate(TaxRate.HIGH, ScoreCategory.HOARD)]

    kept = catalog.legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates)

    assert kept == []
