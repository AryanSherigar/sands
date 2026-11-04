"""Narrator-only instructions (group T): acts, sanity tiers, seed tells, and the
facts the narrator must not contradict."""

from scripts.night_desk import prose, timeline
from scripts.night_desk.expr import Cond, all_of, eq, gte, lt, window

SHIFT = "shift_minutes"
SANITY = "sanity"
SANITY_CEILING = 100


def act_instructions() -> list[Cond]:
    bounds = (
        (0, timeline.ACT2_START),
        (timeline.ACT2_START, timeline.ACT3_START),
        (timeline.ACT3_START, None),
    )
    return [
        Cond(f"T0{number} Act {number} register", _range(SHIFT, low, high), (), text)
        for number, ((low, high), text) in enumerate(
            zip(bounds, prose.ACT_INSTRUCTIONS, strict=True), start=1
        )
    ]


def _range(field: str, low: int, high: int | None) -> dict[str, object]:
    if low <= 0:
        return lt(field, high) if high is not None else gte(field, 0)
    if high is None:
        return gte(field, low)
    return all_of(window(field, low, high))


def sanity_tiers() -> list[Cond]:
    conditions: list[Cond] = []
    for number, tier in enumerate(prose.SANITY_TIERS, start=1):
        upper = None if tier.highest >= SANITY_CEILING else tier.highest + 1
        conditions.append(
            Cond(
                f"T1{number} Sanity tier {tier.name}",
                _tier_expression(tier.lowest, upper),
                (),
                tier.instruction,
            )
        )
    return conditions


def _tier_expression(low: int | None, upper: int | None) -> dict[str, object]:
    if low is None:
        return lt(SANITY, upper if upper is not None else 0)
    if upper is None:
        return gte(SANITY, low)
    return all_of(window(SANITY, low, upper))


def seed_tells() -> list[Cond]:
    lamp_out = eq("cabin.lamp", "out")
    return [
        Cond(
            "T21 Tell: stillness unsafe",
            all_of(lamp_out, eq("seed.false_rule", "r4")),
            (),
            prose.TELL_STILLNESS_UNSAFE,
        ),
        Cond(
            "T22 Tell: entry unsafe",
            all_of(lamp_out, eq("seed.false_rule", "r6")),
            (),
            prose.TELL_ENTRY_UNSAFE,
        ),
    ]


def rule_facts() -> list[Cond]:
    return [
        Cond(
            "T30 Rule 6 hand: leaning",
            eq("rule_status.r6", "intact"),
            (),
            prose.BEATS["r6_hand_leaning"],
            is_fact=True,
        ),
        Cond(
            "T31 Rule 6 hand: block",
            eq("rule_status.r6_block", "intact"),
            (),
            prose.BEATS["r6_hand_block"],
            is_fact=True,
        ),
        Cond(
            "T32 Line 14 lit",
            eq("flags.line14_lit", True),
            (),
            "The lamp for line 14 on the desk phone stays lit.",
            is_fact=True,
        ),
    ]


def ambient_details() -> list[Cond]:
    return [
        Cond(
            f"T4{index + 1:02d} Ambient detail {index + 1}",
            all_of(window(SHIFT, minute, minute + timeline.STEP)),
            (),
            prose.AMBIENT_TEMPLATE.format(line=line),
        )
        for index, line in enumerate(prose.AMBIENT_DECK)
        for minute in (index * timeline.STEP,)
    ]
