"""Result handlers (group H): the consequences a rule-check option cannot carry
itself, because they depend on the seed, a timeout or a client effect.

Every handler includes ALWAYS so it acts on the turn the answer arrives; the
lamp handlers also clear the slot so the next lamp-out can reopen it.
"""

from scripts.night_desk import prose
from scripts.night_desk.consequences import (
    cardinal_violation,
    soft_violation,
    unsafe_entry,
)
from scripts.night_desk.expr import (
    ALWAYS,
    INCREMENT,
    SET,
    Cond,
    Expression,
    Mut,
    all_of,
    eq,
    is_in,
)
from scripts.night_desk.ids import entity_ref

LAMP = "check.lamp"
PHONE = "check.phone"
LOCATION = "current_location_id"
SEED = "seed.false_rule"
LAMP_HELD = ("held_still", "timeout")
TAKEOVER_LOCK_MS = (4500, 5500)
TAKEOVER_TYPE_MS_PER_CHAR = 60
ECHO_RECORD_MS = 6000
ECHO_DELAY_MS = 2500
OUTCOMES = prose.LAMP_OUTCOMES
COUNT_NUMBERS = (1, 2, 3)


def _lamp_back_on() -> tuple[Mut, ...]:
    return (Mut("cabin.lamp", SET, "on"), Mut(LAMP, SET, ""))


def _lamp_handler(
    label: str,
    result: Expression,
    seed: str,
    outcome: str,
    mutations: tuple[Mut, ...] = (),
) -> Cond:
    return Cond(
        label,
        all_of(result, eq(SEED, seed), ALWAYS),
        (*mutations, *_lamp_back_on()),
        OUTCOMES[outcome],
    )


def _entered(slug: str) -> tuple[Mut, ...]:
    return (
        Mut("flags.cabin_entered", SET, True),
        Mut(LOCATION, SET, entity_ref(slug)),
    )


def lamp_handlers() -> list[Cond]:
    held = is_in(LAMP, LAMP_HELD)
    moved = eq(LAMP, "moved")
    entered = eq(LAMP, "entered")
    return [
        _lamp_handler("H01 Lamp held, R4 true", held, "r6", "held_safe"),
        _lamp_handler(
            "H02 Lamp held, R4 false",
            held,
            "r4",
            "held_unsafe",
            cardinal_violation("r4"),
        ),
        _lamp_handler(
            "H03 Lamp moved, R4 true",
            moved,
            "r6",
            "moved_unsafe",
            soft_violation("r4"),
        ),
        _lamp_handler("H04 Lamp moved, R4 false", moved, "r4", "moved_safe"),
        _lamp_handler(
            "H05 Lamp entered, R6 true",
            entered,
            "r4",
            "entered_safe",
            (*_entered("cabin_14"), Mut("visited.cabin_14", SET, True)),
        ),
        _lamp_handler(
            "H06 Lamp entered, R6 false",
            entered,
            "r6",
            "entered_unsafe",
            (*unsafe_entry(), *_entered("east_corridor")),
        ),
    ]


def count_timeout_handlers() -> list[Cond]:
    return [
        Cond(
            f"H0{number + 6} Count {number} timed out",
            all_of(eq(f"count.c{number}", "timeout"), ALWAYS),
            (
                Mut(f"count.c{number}", SET, "left"),
                Mut("count.unsigned", INCREMENT, 1),
            ),
        )
        for number in COUNT_NUMBERS
    ]


def _takeover(label: str, reads: int, line: str, lock_ms: int) -> Cond:
    effect = {
        "kind": "input_takeover",
        "params": {
            "text": line,
            "lock_ms": lock_ms,
            "type_ms_per_char": TAKEOVER_TYPE_MS_PER_CHAR,
        },
    }
    return Cond(
        label,
        all_of(eq("count.reads_after_two", reads), ALWAYS),
        is_one_shot=True,
        effect=effect,
        instruction="",
        mutations=(),
    )


def client_effect_handlers() -> list[Cond]:
    first, second = prose.TAKEOVER_LINES
    echo = {
        "kind": "phone_echo",
        "params": {"record_ms": ECHO_RECORD_MS, "delay_ms": ECHO_DELAY_MS},
    }
    return [
        _takeover("H10 Takeover line 1", 1, first, TAKEOVER_LOCK_MS[0]),
        _takeover("H11 Takeover line 2", 2, second, TAKEOVER_LOCK_MS[1]),
        Cond(
            "H12 Phone echo",
            all_of(eq(PHONE, "picked_up"), ALWAYS),
            instruction=prose.BEATS["phone_after_pickup"],
            is_one_shot=True,
            effect=echo,
        ),
    ]


def answer_handlers() -> list[Cond]:
    return [
        Cond(
            "H13 Visitor unanswered",
            all_of(eq("visit.result", "none"), ALWAYS),
            (Mut("count.wrong_entries", INCREMENT, 1), Mut("visit.pending", SET, "")),
            is_one_shot=False,
        ),
        Cond(
            "H14 Phone let ring",
            all_of(is_in(PHONE, ("let_ring", "timeout")), ALWAYS),
            (Mut("rule_status.r3", SET, "intact"),),
            prose.BEATS["phone_let_ring"],
            is_one_shot=True,
        ),
        Cond(
            "H15 Phone unplugged",
            all_of(eq(PHONE, "unplugged"), ALWAYS),
            (Mut("rule_status.r3", SET, "intact"),),
            is_one_shot=True,
        ),
        Cond(
            "H16 Voicemail played",
            all_of(eq("check.voicemail", "yes"), ALWAYS),
            instruction=prose.BEATS["voicemail"],
            is_one_shot=True,
        ),
    ]


def result_handlers() -> list[Cond]:
    return [
        *lamp_handlers(),
        *count_timeout_handlers(),
        *client_effect_handlers(),
        *answer_handlers(),
    ]
