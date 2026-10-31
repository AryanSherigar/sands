from app.engine.ai.candidates import Candidate, ScoredCandidate
from app.engine.ai.rescoring import outrage_rescorer
from app.models.orders import BuildImprovementOrder, DeclareWarOrder
from strategy_contracts.enums import ImprovementKind
from strategy_contracts.scene import OutrageLevel
from strategy_contracts.stances import ScoreCategory

from tests.engine.outrage.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
    set_axes,
)

TUNING = SCENARIO.tuning.outrage
BASE = 10


def _scored(faction_id: str, category: ScoreCategory) -> ScoredCandidate:
    if category == ScoreCategory.ATTACK:
        order = DeclareWarOrder(faction_id=faction_id, target_faction_id=PLAYER)
    else:
        order = BuildImprovementOrder(
            faction_id=faction_id,
            region_id="home",
            improvement_kind=ImprovementKind.BARRACKS,
        )
    return ScoredCandidate(
        Candidate(order=order, category=category),
        score=BASE,
        trait_score=0,
        stance_score=0,
    )


def _rescore(world, scenario, *categories: ScoreCategory) -> list[ScoredCandidate]:
    scored = [_scored(WRATHFUL_RIVAL, category) for category in categories]
    return outrage_rescorer(world, scenario, WRATHFUL_RIVAL, scored)


def test_a_proud_enraged_ruler_favors_attack_over_defense() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3)
    enrage(world)

    attack, build = _rescore(world, scenario, ScoreCategory.ATTACK, ScoreCategory.BUILD)

    assert attack.score > BASE
    assert build.score < BASE
    assert attack.adjustment == attack.score - BASE


def test_hoarding_counts_as_defense_too() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3)
    enrage(world)

    (hoard,) = _rescore(world, scenario, ScoreCategory.HOARD)

    assert hoard.score < BASE


def test_a_calm_ruler_is_scored_as_usual() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3)

    attack, build = _rescore(world, scenario, ScoreCategory.ATTACK, ScoreCategory.BUILD)

    assert (attack.score, build.score) == (BASE, BASE)


def test_a_calculating_ruler_keeps_their_head() -> None:
    world = make_world()
    scenario = set_axes(
        world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3, cunning=3
    )
    enrage(world)

    attack, build = _rescore(world, scenario, ScoreCategory.ATTACK, ScoreCategory.BUILD)

    assert (attack.score, build.score) == (BASE, BASE)


def test_a_cautious_ruler_barely_shifts() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=1, caution=3)
    enrage(world)

    (attack,) = _rescore(world, scenario, ScoreCategory.ATTACK)

    assert attack.score == BASE


def test_a_merely_offended_ruler_does_not_overreact() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3)
    enrage(world, level=OutrageLevel.OFFENDED)

    (attack,) = _rescore(world, scenario, ScoreCategory.ATTACK)

    assert attack.score == BASE


def test_the_bias_never_applies_to_other_factions() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, pride=3, aggression=3)
    enrage(world)
    scored = [_scored(PLAYER, ScoreCategory.ATTACK)]

    result = outrage_rescorer(world, scenario, PLAYER, scored)

    assert result[0].score == BASE
