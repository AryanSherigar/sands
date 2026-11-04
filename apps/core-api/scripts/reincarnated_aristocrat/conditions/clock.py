"""Group G: the turn counter, the clock and Ars's birthdays."""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.conditions.common import (
    CLOCK,
    NO_VALUE,
    TURNS,
    clear,
    label,
)
from scripts.reincarnated_aristocrat.schema import (
    ARS_START_AGE,
    CLOCK_MAX_DAYS,
    TIME_COSTS,
    TURNS_MAX,
)
from scripts.seeding.expr import INCREMENT, SET, Cond, Mut, all_of, eq, gte, lt

AGE = "player.age"


def ticks() -> list[Cond]:
    return [
        Cond(
            label("G", 1, "Turn counter"),
            lt(TURNS, TURNS_MAX),
            (Mut(TURNS, INCREMENT, 1),),
        ),
        Cond(
            label("G", 2, "Clock advance"),
            lt(CLOCK, CLOCK_MAX_DAYS),
            (Mut(CLOCK, INCREMENT, balance.DAYS_PER_TURN),),
        ),
    ]


def time_costs() -> list[Cond]:
    kinds = [kind for kind in TIME_COSTS if kind != NO_VALUE]
    return [
        Cond(
            label("G", 3 + index, f"Time cost {kind}"),
            eq("intent.time_cost", kind),
            (Mut(CLOCK, INCREMENT, balance.TIME_COST_DAYS[kind]), *clear("time_cost")),
        )
        for index, kind in enumerate(kinds)
    ]


def birthdays() -> list[Cond]:
    first_index = 3 + len(TIME_COSTS)
    return [
        Cond(
            label("G", first_index + age - balance.FIRST_BIRTHDAY_AGE, f"Age {age}"),
            all_of(
                gte(CLOCK, (age - ARS_START_AGE) * balance.DAYS_PER_YEAR),
                lt(AGE, age),
            ),
            (Mut(AGE, SET, age),),
            instruction=f"Ars has just turned {age}. Mention it in one line only.",
            is_one_shot=True,
        )
        for age in range(balance.FIRST_BIRTHDAY_AGE, balance.LAST_BIRTHDAY_AGE + 1)
    ]


def clock_conditions() -> list[Cond]:
    return [*ticks(), *time_costs(), *birthdays()]
