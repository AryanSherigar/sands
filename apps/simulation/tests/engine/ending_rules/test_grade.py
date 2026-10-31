import pytest
from app.engine.ending_rules.grade import (
    compute_grade,
    tier_for_score,
    weighted_score,
)
from strategy_contracts.endings import EndingGrade, EndingsTuning

from tests.engine.ending_rules.builders import PLAYER, make_world, scenario_with
from tests.engine.vassals.builders import CAUTIOUS_RIVAL, add_vassalage

STABILITY_ONLY = {
    "weight_position": 0,
    "weight_stability": 100,
    "weight_treasury": 0,
    "weight_will": 0,
    "weight_strain": 0,
}


@pytest.mark.parametrize(
    ("stability", "expected"),
    [
        (29, EndingGrade.RUIN),
        (30, EndingGrade.BITTER),
        (54, EndingGrade.BITTER),
        (55, EndingGrade.HONORABLE),
        (79, EndingGrade.HONORABLE),
        (80, EndingGrade.TRIUMPH),
    ],
)
def test_grade_tier_boundaries(stability: int, expected: EndingGrade) -> None:
    world = make_world()
    world.factions[PLAYER].stability = stability
    scenario = scenario_with(**STABILITY_ONLY, pyrrhic_position_floor=101)

    assert compute_grade(world, scenario).grade == expected


def test_strain_lowers_score() -> None:
    tuning = EndingsTuning()
    calm = {"position": 50, "stability": 50, "treasury": 50, "will": 50, "strain": 100}
    strained = calm | {"strain": 0}

    assert weighted_score(strained, tuning) < weighted_score(calm, tuning)


def test_tier_for_score_uses_thresholds() -> None:
    tuning = EndingsTuning()
    assert tier_for_score(0, tuning) == EndingGrade.RUIN
    assert tier_for_score(100, tuning) == EndingGrade.TRIUMPH


def test_pyrrhic_when_big_but_strained() -> None:
    world = make_world()
    world.factions[PLAYER].stability = 100
    scenario = scenario_with(
        **STABILITY_ONLY, pyrrhic_position_floor=0, pyrrhic_strain_floor=0
    )

    assert compute_grade(world, scenario).grade == EndingGrade.PYRRHIC


def test_not_pyrrhic_below_the_strain_floor() -> None:
    world = make_world()
    world.factions[PLAYER].stability = 100
    scenario = scenario_with(
        **STABILITY_ONLY, pyrrhic_position_floor=0, pyrrhic_strain_floor=1
    )

    assert compute_grade(world, scenario).grade == EndingGrade.TRIUMPH


def test_peacetime_will_and_strain_components_are_full() -> None:
    reading = compute_grade(make_world(), scenario_with())

    assert reading.inputs["will"] == 100
    assert reading.inputs["strain"] == 100


def test_vassal_grade_capped_even_with_high_score() -> None:
    world = make_world()
    world.factions[PLAYER].stability = 100
    add_vassalage(world, CAUTIOUS_RIVAL, PLAYER)
    scenario = scenario_with(**STABILITY_ONLY, pyrrhic_position_floor=101)

    assert compute_grade(world, scenario).grade == EndingGrade.BITTER


def test_vassal_cap_skipped_when_vassal_outcome_disabled() -> None:
    world = make_world()
    world.factions[PLAYER].stability = 100
    add_vassalage(world, CAUTIOUS_RIVAL, PLAYER)
    scenario = scenario_with(
        **STABILITY_ONLY,
        pyrrhic_position_floor=101,
        toggles={"is_vassal_outcome_enabled": False},
    )

    assert compute_grade(world, scenario).grade == EndingGrade.TRIUMPH
