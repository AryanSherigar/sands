from typing import TypeVar

from app.models.world_army import ArmyState
from strategy_contracts.battle_speech import (
    MAX_REACTION_INTENSITY,
    ArmyMood,
    CrowdMood,
    CrowdReaction,
    ExhaustionBucket,
    MoraleBucket,
    PayBucket,
)
from strategy_contracts.scene import MAX_SPEECH_MORALE_SWING

MORALE_BUCKET_FLOORS: tuple[tuple[int, MoraleBucket], ...] = (
    (90, MoraleBucket.FERVENT),
    (70, MoraleBucket.RESOLUTE),
    (45, MoraleBucket.STEADY),
    (20, MoraleBucket.SHAKEN),
    (0, MoraleBucket.BROKEN),
)
EXHAUSTION_BUCKET_FLOORS: tuple[tuple[int, ExhaustionBucket], ...] = (
    (60, ExhaustionBucket.SPENT),
    (30, ExhaustionBucket.TIRED),
    (0, ExhaustionBucket.FRESH),
)
Bucket = TypeVar("Bucket")
NEUTRAL_REACTION = CrowdReaction(mood=CrowdMood.MURMUR, intensity=1)
GRUMBLING_UNPAID_TURNS = 1
UNPAID_TURNS = 3
INTENSITY_STEP_PERCENT = MAX_SPEECH_MORALE_SWING // MAX_REACTION_INTENSITY

MORALE_LINES: dict[MoraleBucket, str] = {
    MoraleBucket.BROKEN: "the men are close to breaking and say so openly",
    MoraleBucket.SHAKEN: "the men are shaken and keep looking back over their shoulders",
    MoraleBucket.STEADY: "the men are steady enough, no more than that",
    MoraleBucket.RESOLUTE: "the men are in good heart and ready to stand",
    MoraleBucket.FERVENT: "the men are burning for this fight",
}
EXHAUSTION_LINES: dict[ExhaustionBucket, str] = {
    ExhaustionBucket.FRESH: "They are rested and moving easily.",
    ExhaustionBucket.TIRED: "They have marched hard and it shows in their step.",
    ExhaustionBucket.SPENT: "They are spent, barely upright after the long road.",
}
PAY_LINES: dict[PayBucket, str] = {
    PayBucket.PAID: "",
    PayBucket.GRUMBLING: " There is some grumbling about pay.",
    PayBucket.UNPAID: " They have gone unpaid too long and they remember it.",
}


def _first_bucket_at_or_above(
    value: int, floors: tuple[tuple[int, Bucket], ...]
) -> Bucket:
    return next(bucket for floor, bucket in floors if value >= floor)


def _pay_bucket(unpaid_turns: int) -> PayBucket:
    if unpaid_turns >= UNPAID_TURNS:
        return PayBucket.UNPAID
    if unpaid_turns >= GRUMBLING_UNPAID_TURNS:
        return PayBucket.GRUMBLING
    return PayBucket.PAID


def army_mood(army: ArmyState) -> ArmyMood:
    return ArmyMood(
        morale=_first_bucket_at_or_above(army.morale, MORALE_BUCKET_FLOORS),
        exhaustion=_first_bucket_at_or_above(army.fatigue, EXHAUSTION_BUCKET_FLOORS),
        pay=_pay_bucket(army.unpaid_turns),
    )


def officer_report(mood: ArmyMood, officer_name: str) -> str:
    return (
        f"{officer_name}: My lord, {MORALE_LINES[mood.morale]}. "
        f"{EXHAUSTION_LINES[mood.exhaustion]}{PAY_LINES[mood.pay]}"
    )


def reaction_from_delta(morale_delta_percent: int) -> CrowdReaction:
    if morale_delta_percent == 0:
        return NEUTRAL_REACTION
    mood = CrowdMood.CHEER if morale_delta_percent > 0 else CrowdMood.PROTEST
    steps = -(-abs(morale_delta_percent) // INTENSITY_STEP_PERCENT)
    return CrowdReaction(mood=mood, intensity=min(steps, MAX_REACTION_INTENSITY))
