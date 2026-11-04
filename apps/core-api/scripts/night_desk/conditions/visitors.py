"""Visitor presence (group V): a visitor stays for a fixed number of turns, then
leaves, so the narrator is told when to stop describing them.

`visit.present` outlives the time-entry check (which clears `visit.pending`), so a
visitor is still at the desk after the clerk has written them in the Log.
"""

from scripts.night_desk import prose
from scripts.night_desk.expr import (
    ALWAYS,
    INCREMENT,
    SET,
    Cond,
    Mut,
    all_of,
    eq,
    gte,
    ne,
)

PRESENT = "visit.present"
TURNS_PRESENT = "visit.turns_present"
PRESENT_TURN = 2
LETTERS = "abc"


def _presence() -> list[Cond]:
    return [
        Cond(
            f"V02{LETTERS[index]} {visitor.name} present",
            all_of(eq(PRESENT, visitor_id), eq(TURNS_PRESENT, PRESENT_TURN)),
            instruction=prose.VISITOR_PRESENT.format(name=visitor.name),
        )
        for index, (visitor_id, visitor) in enumerate(prose.VISITORS.items())
    ]


def _departures() -> list[Cond]:
    return [
        Cond(
            f"V03{LETTERS[index]} {visitor.name} leaves",
            all_of(
                eq(PRESENT, visitor_id), gte(TURNS_PRESENT, visitor.stays_for_turns)
            ),
            (Mut(PRESENT, SET, ""), Mut(TURNS_PRESENT, SET, 0)),
            prose.VISITOR_DEPARTURE.format(name=visitor.name),
        )
        for index, (visitor_id, visitor) in enumerate(prose.VISITORS.items())
    ]


def visitor_presence() -> list[Cond]:
    return [
        Cond(
            "V01 Visitor turn count",
            ne(PRESENT, ""),
            (Mut(TURNS_PRESENT, INCREMENT, 1),),
        ),
        *_presence(),
        *_departures(),
        Cond(
            "V04 Log result consumed",
            all_of(ne("visit.result", ""), ALWAYS),
            (Mut("visit.result", SET, ""),),
        ),
    ]
