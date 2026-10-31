from app.engine.ai.generators.economy import tax_rate_candidates
from app.models.orders import SetTaxRateOrder
from strategy_contracts.enums import TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, SCENARIO, make_world


def _by_rate(world, faction_id):
    candidates = tax_rate_candidates(world, SCENARIO, faction_id)
    return {candidate.order.tax_rate: candidate for candidate in candidates}


def test_tax_candidates_exclude_current_rate() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].tax_rate = TaxRate.NORMAL

    by_rate = _by_rate(world, CAUTIOUS_RIVAL)

    assert set(by_rate) == {TaxRate.LOW, TaxRate.HIGH}
    assert all(isinstance(item.order, SetTaxRateOrder) for item in by_rate.values())


def test_tax_high_is_hoard_and_low_is_build() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].tax_rate = TaxRate.NORMAL

    by_rate = _by_rate(world, CAUTIOUS_RIVAL)

    assert by_rate[TaxRate.HIGH].category == ScoreCategory.HOARD
    assert by_rate[TaxRate.LOW].category == ScoreCategory.BUILD


def test_tax_candidates_belong_to_the_asking_faction() -> None:
    world = make_world()

    candidates = tax_rate_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert {item.order.faction_id for item in candidates} == {CAUTIOUS_RIVAL}


def test_tax_change_carries_a_status_quo_penalty() -> None:
    world = make_world()

    candidates = tax_rate_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert all(item.base_score < 0 for item in candidates)
