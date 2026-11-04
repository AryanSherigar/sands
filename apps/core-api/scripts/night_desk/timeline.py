"""Clock constants and the beat timeline (shift_minutes: 0 = 11:00 PM).

The clock advances by one fixed step per turn, so the number of turns is
deterministic. A timed condition is a one-shot threshold on the pre-advance
shift_minutes: it fires on the first turn whose clock is at or past its time, so
a turn that is skipped or doubled up can never lose a beat
(docs/specs/rules-horror-night-desk-data.md §4).
"""

from typing import NamedTuple

STEP = 20
SHIFT_END = 420
ACT2_START = 140
ACT3_START = 260
EXPECTED_TURN_COUNT = 21
COUNT_MINUTES = (120, 240, 360)

BEATS: dict[str, int] = {
    "visitor_1": 40,
    "drawer": 80,
    "count_1": 120,
    "r6_appears": 140,
    "visitor_2": 160,
    "printer_r7": 180,
    "lamp_out": 200,
    "count_2": 240,
    "phone": 260,
    "voicemail": 280,
    "visitor_3": 300,
    "stairwell": 320,
    "count_3": 360,
    "elevator_empty": 380,
}


class Drain(NamedTuple):
    start: int
    amount: int


DRAINS: tuple[Drain, ...] = (
    Drain(60, 2),
    Drain(180, 2),
    Drain(220, 2),
    Drain(300, 3),
    Drain(380, 3),
)


def turns_to_dawn() -> int:
    return len(range(0, SHIFT_END, STEP))
