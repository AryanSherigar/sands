"""Paths, flags and label helpers shared by every condition group."""

from scripts.reincarnated_aristocrat.ids import entity_id
from scripts.seeding.expr import (
    DECREMENT,
    INCREMENT,
    SET,
    Expression,
    Mut,
    eq,
    ref_gte,
)

CLOCK = "time.clock_days"
TURNS = "time.turns"
NEXT_INCOME = "time.next_income_day"
NO_VALUE = ""
NO_REPEAT_MARKER = (
    " The intent marker for this was already applied: do not write it again."
)
GROUP_ORDER = ("G", "B", "A", "R", "T", "P", "M", "W")


def attr(slug: str, name: str) -> str:
    return f"{entity_id(slug)}.{name}"


def is_due() -> Expression:
    return ref_gte(CLOCK, NEXT_INCOME)


def is_recruited(slug: str) -> Expression:
    return eq(attr(slug, "is_recruited"), True)


def label(group: str, index: int, text: str) -> str:
    return f"{group}{index:02d} {text}"


def clear(*flags: str) -> tuple[Mut, ...]:
    return tuple(Mut(f"intent.{flag}", SET, NO_VALUE) for flag in flags)


def change(path: str, delta: int) -> Mut:
    """An increment for a positive delta and a decrement for a negative one."""
    if delta >= 0:
        return Mut(path, INCREMENT, delta)
    return Mut(path, DECREMENT, -delta)
