"""Passive sanity drain and the clock advance (groups D and A)."""

from scripts.night_desk import timeline
from scripts.night_desk.expr import (
    DECREMENT,
    INCREMENT,
    Cond,
    Mut,
    gte,
    lt,
)

SHIFT = "shift_minutes"


def drains() -> list[Cond]:
    return [
        Cond(
            f"D{index:02d} Passive drain at {drain.start}",
            gte(SHIFT, drain.start),
            (Mut("sanity", DECREMENT, drain.amount),),
            is_one_shot=True,
        )
        for index, drain in enumerate(timeline.DRAINS, start=1)
    ]


def advance() -> list[Cond]:
    return [
        Cond(
            "A01 Clock advance",
            lt(SHIFT, timeline.SHIFT_END),
            (Mut(SHIFT, INCREMENT, timeline.STEP),),
        )
    ]
