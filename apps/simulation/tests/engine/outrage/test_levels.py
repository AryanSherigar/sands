import pytest
from app.engine.outrage.levels import demand_price_percent, outrage_level
from strategy_contracts.outrage import OutrageTuning
from strategy_contracts.scene import OutrageLevel

TUNING = OutrageTuning()
NEUTRAL = 0
PROUD = 3
HUMBLE = -3
NO_TONE = None


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (10, OutrageLevel.NONE),
        (25, OutrageLevel.ANNOYED),
        (60, OutrageLevel.OFFENDED),
        (100, OutrageLevel.OUTRAGED),
        (400, OutrageLevel.ENRAGED),
    ],
)
def test_price_over_score_maps_to_a_level(percent: int, expected: OutrageLevel) -> None:
    assert outrage_level(percent, NEUTRAL, NO_TONE, TUNING) == expected


def test_a_proud_leader_feels_it_one_step_worse() -> None:
    assert outrage_level(60, PROUD, NO_TONE, TUNING) == OutrageLevel.OUTRAGED


def test_a_humble_leader_feels_it_one_step_milder() -> None:
    assert outrage_level(60, HUMBLE, NO_TONE, TUNING) == OutrageLevel.ANNOYED


def test_a_sharp_tone_shifts_one_more_step() -> None:
    assert outrage_level(60, NEUTRAL, 5, TUNING) == OutrageLevel.OUTRAGED


def test_a_gentle_tone_softens_one_step() -> None:
    assert outrage_level(60, NEUTRAL, 0, TUNING) == OutrageLevel.ANNOYED


def test_a_middling_tone_changes_nothing() -> None:
    assert outrage_level(60, NEUTRAL, 3, TUNING) == OutrageLevel.OFFENDED


def test_shifts_never_leave_the_ladder() -> None:
    assert outrage_level(400, PROUD, 5, TUNING) == OutrageLevel.ENRAGED
    assert outrage_level(0, HUMBLE, 0, TUNING) == OutrageLevel.NONE


def test_price_is_measured_against_the_demanders_score() -> None:
    assert demand_price_percent(demand=30, demander_score=60, tuning=TUNING) == 50


def test_a_demander_without_score_is_floored_not_divided_by_zero() -> None:
    percent = demand_price_percent(demand=10, demander_score=0, tuning=TUNING)

    assert percent == 10 * 100 // TUNING.min_demander_score
