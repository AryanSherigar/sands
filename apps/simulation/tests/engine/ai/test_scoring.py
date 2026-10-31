from app.engine.ai.candidates import Candidate
from app.engine.ai.scoring import score_candidate
from app.models.orders import SetTaxRateOrder
from strategy_contracts.enums import TaxRate
from strategy_contracts.stances import BUILTIN_STANCES, ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

STANCE_WEIGHT = SCENARIO.tuning.ai.stance_weight


def _candidate(category: ScoreCategory, base_score: int = 0) -> Candidate:
    order = SetTaxRateOrder(faction_id=WRATHFUL_RIVAL, tax_rate=TaxRate.HIGH)
    return Candidate(order=order, category=category, base_score=base_score)


def _shift(stance_id: str, category: ScoreCategory) -> int:
    stance = next(item for item in BUILTIN_STANCES if item.id == stance_id)
    return stance.shifts.get(category, 0)


def test_aggressive_leader_scores_attack_above_hoard() -> None:
    world = make_world()
    set_traits(world, WRATHFUL_RIVAL, ["wrathful"])

    attack = score_candidate(
        world, SCENARIO, WRATHFUL_RIVAL, _candidate(ScoreCategory.ATTACK)
    )
    hoard = score_candidate(
        world, SCENARIO, WRATHFUL_RIVAL, _candidate(ScoreCategory.HOARD)
    )

    assert attack.trait_score > hoard.trait_score
    assert attack.score == attack.trait_score


def test_stance_expand_raises_expand_score_by_shift_times_weight() -> None:
    world = make_world()
    set_traits(world, WRATHFUL_RIVAL, [])
    world.factions[WRATHFUL_RIVAL].stance.option_id = "expand"

    scored = score_candidate(
        world, SCENARIO, WRATHFUL_RIVAL, _candidate(ScoreCategory.EXPAND, 3)
    )

    expected = _shift("expand", ScoreCategory.EXPAND) * STANCE_WEIGHT
    assert scored.stance_score == expected
    assert scored.score == 3 + expected


def test_no_stance_gives_zero_stance_score() -> None:
    world = make_world()
    set_traits(world, WRATHFUL_RIVAL, [])

    scored = score_candidate(
        world, SCENARIO, WRATHFUL_RIVAL, _candidate(ScoreCategory.EXPAND)
    )

    assert scored.stance_score == 0


def test_missing_leader_gives_zero_trait_and_stance_score() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].leader_id = None
    world.factions[CAUTIOUS_RIVAL].stance.option_id = "expand"

    scored = score_candidate(
        world, SCENARIO, CAUTIOUS_RIVAL, _candidate(ScoreCategory.EXPAND)
    )

    assert (scored.trait_score, scored.stance_score) == (0, 0)
