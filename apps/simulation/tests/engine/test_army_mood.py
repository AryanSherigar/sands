import pytest
from app.engine.army_mood import army_mood, officer_report, reaction_from_delta
from app.models.world_army import ArmyState
from pydantic import ValidationError
from strategy_contracts.battle_speech import (
    ArmyMood,
    CrowdMood,
    CrowdReaction,
    ExhaustionBucket,
    MoraleBucket,
    PayBucket,
)


def _army(morale: int = 55, fatigue: int = 0, unpaid_turns: int = 0) -> ArmyState:
    return ArmyState(
        id="army_a",
        owner_id="house_a",
        morale=morale,
        fatigue=fatigue,
        location_id="region_a",
        unpaid_turns=unpaid_turns,
    )


@pytest.mark.parametrize(
    ("morale", "expected"),
    [
        (5, MoraleBucket.BROKEN),
        (30, MoraleBucket.SHAKEN),
        (55, MoraleBucket.STEADY),
        (75, MoraleBucket.RESOLUTE),
        (95, MoraleBucket.FERVENT),
    ],
)
def test_morale_buckets_cover_range(morale: int, expected: MoraleBucket) -> None:
    assert army_mood(_army(morale=morale)).morale == expected


def test_exhaustion_and_morale_are_independent() -> None:
    mood = army_mood(_army(morale=95, fatigue=90))
    assert mood.morale == MoraleBucket.FERVENT
    assert mood.exhaustion == ExhaustionBucket.SPENT


@pytest.mark.parametrize(
    ("unpaid_turns", "expected"),
    [(0, PayBucket.PAID), (1, PayBucket.GRUMBLING), (3, PayBucket.UNPAID)],
)
def test_unpaid_turns_map_to_pay_bucket(unpaid_turns: int, expected: PayBucket) -> None:
    assert army_mood(_army(unpaid_turns=unpaid_turns)).pay == expected


def test_officer_report_is_deterministic_and_has_no_digits() -> None:
    mood = ArmyMood(
        morale=MoraleBucket.SHAKEN,
        exhaustion=ExhaustionBucket.SPENT,
        pay=PayBucket.UNPAID,
    )
    first = officer_report(mood, "Captain Hale")
    assert first == officer_report(mood, "Captain Hale")
    assert not any(character.isdigit() for character in first)
    assert "Captain Hale" in first


def test_reaction_from_delta_is_monotonic_at_the_extremes() -> None:
    assert reaction_from_delta(-15) == CrowdReaction(
        mood=CrowdMood.PROTEST, intensity=3
    )
    assert reaction_from_delta(0) == CrowdReaction(mood=CrowdMood.MURMUR, intensity=1)
    assert reaction_from_delta(15) == CrowdReaction(mood=CrowdMood.CHEER, intensity=3)


def test_reaction_intensity_never_drops_moving_away_from_zero() -> None:
    positive = [reaction_from_delta(delta).intensity for delta in range(0, 16)]
    negative = [reaction_from_delta(-delta).intensity for delta in range(0, 16)]
    assert positive == sorted(positive)
    assert negative == sorted(negative)


def test_crowd_reaction_rejects_out_of_range_intensity() -> None:
    with pytest.raises(ValidationError):
        CrowdReaction(mood=CrowdMood.CHEER, intensity=4)
