import pytest
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.peace import PeaceTier, PeaceTuning
from strategy_contracts.scenario import Tuning
from strategy_contracts.scene import SceneType
from strategy_contracts.terms import PeaceTerm, TermKind, TermsCard

TIER_ORDER = (
    PeaceTier.SHORT,
    PeaceTier.MEDIUM,
    PeaceTier.GENERATION,
    PeaceTier.PERPETUAL,
)


def test_defaults_are_monotonic() -> None:
    tuning = Tuning().peace

    costs = [tuning.tier_score_cost[tier] for tier in TIER_ORDER]
    turns = [tuning.tier_turns[tier] for tier in TIER_ORDER[:3]]
    assert costs == sorted(set(costs))
    assert turns == sorted(set(turns))


def test_perpetual_never_expires() -> None:
    assert Tuning().peace.tier_turns[PeaceTier.PERPETUAL] == 0


def test_non_monotonic_score_costs_are_rejected() -> None:
    costs = {
        PeaceTier.SHORT: 20,
        PeaceTier.MEDIUM: 5,
        PeaceTier.GENERATION: 15,
        PeaceTier.PERPETUAL: 30,
    }
    with pytest.raises(ValidationError):
        PeaceTuning(tier_score_cost=costs)


def test_every_tier_needs_a_cost_and_a_length() -> None:
    with pytest.raises(ValidationError):
        PeaceTuning(tier_turns={PeaceTier.SHORT: 6})


def test_peace_term_round_trips_in_terms_card() -> None:
    term = PeaceTerm(faction_a="crown_a", faction_b="crown_b", tier=PeaceTier.MEDIUM)
    card = TermsCard(proposer_id="crown_a", counterpart_id="crown_b", terms=[term])

    assert TermsCard.model_validate_json(card.model_dump_json()) == card
    assert card.terms[0].kind == TermKind.PEACE.value


def test_peace_scene_type_exists() -> None:
    assert SceneType.PEACE.value == "peace"


def test_three_crowns_loads_with_default_peace_tuning() -> None:
    assert load_three_crowns().tuning.peace == PeaceTuning()


def test_term_pricing_defaults() -> None:
    tuning = PeaceTuning()

    assert tuning.cede_region_score_cost == 15
    assert tuning.gold_per_score_point == 50
    assert tuning.broken_will_ceiling == 20
    with pytest.raises(ValidationError):
        PeaceTuning(gold_per_score_point=0)
