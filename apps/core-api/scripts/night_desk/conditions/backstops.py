"""State-observable rule backstops and visit bookkeeping (group P)."""

from scripts.night_desk import prose
from scripts.night_desk.consequences import cardinal_violation, soft_violation
from scripts.night_desk.expr import (
    ALWAYS,
    INCREMENT,
    SET,
    Cond,
    Expression,
    Mut,
    all_of,
    either,
    eq,
    gte,
    ne,
)
from scripts.night_desk.ids import entity_ref

LOCATION = "current_location_id"
ALCOVE_DWELL_LIMIT = 2
VISITED_LAST = "visited.last"
LEFT_RECORDS = "elsewhere"


def at(slug: str) -> Expression:
    return eq(LOCATION, entity_ref(slug))


def alcove_rule() -> list[Cond]:
    """R2: activate on the corridor; violate on a long dwell or a narrator flag.

    The narrator flag (`rule_flags.r2`, set by flag_rule_violation) is the
    AI-judged path; the dwell counter is the deterministic backstop.
    """
    dwell = "dwell.alcove"
    violation = all_of(
        ne("rule_status.r2", "violated"),
        either(gte(dwell, ALCOVE_DWELL_LIMIT), eq("rule_flags.r2", True)),
    )
    return [
        Cond(
            "P01 R2 active",
            all_of(at("east_corridor"), eq("rule_status.r2", "intact")),
            (Mut("rule_status.r2", SET, "active_threat"),),
        ),
        Cond("P02a Alcove dwell", at("east_alcove"), (Mut(dwell, INCREMENT, 1),)),
        Cond(
            "P02b Alcove left",
            all_of(ne(LOCATION, entity_ref("east_alcove")), gte(dwell, 1)),
            (Mut(dwell, SET, 0),),
        ),
        Cond(
            "P02c R2 violated",
            violation,
            (
                *soft_violation("r2"),
                Mut(dwell, SET, 0),
                Mut("rule_flags.r2", SET, False),
            ),
            is_one_shot=True,
        ),
    ]


def approach_rule() -> list[Cond]:
    return [
        Cond(
            "P03 R4 approach",
            all_of(at("cabin_approach"), eq("cabin.lamp", "on"), ALWAYS),
            (
                *cardinal_violation("r4"),
                Mut(LOCATION, SET, entity_ref("east_corridor")),
            ),
            prose.BEATS["cabin_locked"],
        )
    ]


def visits() -> list[Cond]:
    """Records is counted once per visit, not once per turn spent there."""
    return [
        Cond(
            "P04 Records visit",
            all_of(at("records_room"), ne(VISITED_LAST, "records_room")),
            (
                Mut("visited.records_room", INCREMENT, 1),
                Mut(VISITED_LAST, SET, "records_room"),
            ),
        ),
        Cond(
            "P05 Records left",
            all_of(
                ne(LOCATION, entity_ref("records_room")),
                eq(VISITED_LAST, "records_room"),
            ),
            (Mut(VISITED_LAST, SET, LEFT_RECORDS),),
        ),
        _first_entry("P06 Print room entered", "print_room"),
        _first_entry("P07 Elevator lobby entered", "elevator_lobby"),
        _first_entry("P08 Cabin 14 entered", "cabin_14"),
    ]


def _first_entry(label: str, slug: str) -> Cond:
    return Cond(
        label,
        at(slug),
        (Mut(f"visited.{slug}", SET, True),),
        is_one_shot=True,
    )


def backstops() -> list[Cond]:
    return [*alcove_rule(), *approach_rule(), *visits()]
