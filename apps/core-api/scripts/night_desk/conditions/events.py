"""Timed events (group E): one one-shot threshold condition per beat, with every
mutation, the narrator instruction and the cue in the same condition."""

from scripts.night_desk import prose, timeline
from scripts.night_desk.conditions.backstops import at
from scripts.night_desk.expr import (
    ALWAYS,
    INCREMENT,
    SET,
    Cond,
    Cue,
    Expression,
    Mut,
    all_of,
    eq,
    gte,
    is_in,
    lt,
    ne,
)

SHIFT = "shift_minutes"
TIER = "tension_tier"
SANITY = "sanity"
SANITY_BREAKING_BELOW = 25
CHIME = Cue("elevator_chime")
PAPER = Cue("paper_rustle")
LAMP_CLICK = Cue("lamp_click", cut_ambient=True, silence_ms=400)
SILENCE = Cue("sudden_silence", cut_ambient=True, silence_ms=800)
PHONE_RING = Cue("phone_ring", cut_ambient=True, silence_ms=800)
WRONG_ENTRY_RESULTS = ("wall", "other", "rejected", "none")
BEATS = timeline.BEATS


def _after(key: str, *guards: Expression) -> Expression:
    return all_of(gte(SHIFT, BEATS[key]), *guards)


def _status(rule: str, value: str) -> Mut:
    return Mut(f"rule_status.{rule}", SET, value)


def _timed(
    label: str,
    when: Expression,
    mutations: tuple[Mut, ...] = (),
    instruction: str = "",
    cue: Cue | None = None,
) -> Cond:
    return Cond(label, when, mutations, instruction, cue, is_one_shot=True)


def _arrival(label: str, key: str, visitor_id: str) -> Cond:
    visitor = prose.VISITORS[visitor_id]
    arrival = prose.VISITOR_ARRIVAL.format(
        name=visitor.name, look=visitor.look, told=visitor.told, line=visitor.line
    )
    return _timed(
        label,
        _after(key, eq("visit.pending", ""), eq("visit.present", "")),
        (
            Mut("visit.pending", SET, visitor_id),
            Mut("visit.present", SET, visitor_id),
            Mut("visit.turns_present", SET, 0),
        ),
        arrival,
        CHIME,
    )


def _early_events() -> list[Cond]:
    return [
        _arrival("E01 Visitor 1 arrives", "visitor_1", "v1"),
        _timed(
            "E02 Drawer prompt",
            _after("drawer", at("night_desk"), lt(SHIFT, timeline.ACT2_START)),
            (Mut("check.drawer", SET, "pending"),),
        ),
        _timed(
            "E03 Count 1",
            _after("count_1"),
            (Mut("count.c1", SET, "pending"),),
            cue=PAPER,
        ),
        Cond(
            "E04 Count difference",
            all_of(is_in("visit.result", WRONG_ENTRY_RESULTS), ALWAYS),
            (Mut("count.difference", INCREMENT, 1),),
        ),
        _rule_six("E05 Rule 6 appears, seed r4", "r4", "r6"),
        _rule_six("E06 Rule 6 appears, seed r6", "r6", "r6_block"),
    ]


def _rule_six(label: str, seed: str, rule: str) -> Cond:
    return _timed(
        label,
        _after("r6_appears", eq("seed.false_rule", seed)),
        (_status(rule, "intact"), Mut(TIER, SET, "tense")),
        prose.BEATS["r6_appears"],
        Cue("lamp_click"),
    )


def _middle_events() -> list[Cond]:
    return [
        _arrival("E07 Visitor 2 arrives", "visitor_2", "v2"),
        _timed(
            "E08 Printer prints rule 7",
            _after("printer_r7"),
            (_status("r7", "intact"),),
            prose.BEATS["printer_r7"],
            PAPER,
        ),
        _timed(
            "E09 Lamp out",
            _after("lamp_out"),
            (Mut("cabin.lamp", SET, "out"), Mut("check.lamp", SET, "pending")),
            prose.BEATS["lamp_out"],
            LAMP_CLICK,
        ),
        _timed(
            "E10 Count 2",
            _after("count_2"),
            (Mut("count.c2", SET, "pending"), Mut(TIER, SET, "dread")),
            cue=PAPER,
        ),
    ]


def _late_events() -> list[Cond]:
    return [
        _timed(
            "E11 Phone rings",
            _after("phone"),
            (Mut("check.phone", SET, "pending"), _status("r3", "active_threat")),
            prose.BEATS["phone"],
            PHONE_RING,
        ),
        _timed(
            "E12 Voicemail waiting",
            _after("voicemail"),
            (Mut("check.voicemail", SET, "pending"),),
        ),
        _arrival("E13 Visitor 3 arrives", "visitor_3", "v3"),
        _timed(
            "E14 Stairwell voice",
            _after("stairwell"),
            (Mut("events.stairwell", SET, True),),
            prose.BEATS["stairwell"],
            SILENCE,
        ),
        _timed(
            "E15 Count 3",
            _after("count_3"),
            (Mut("count.c3", SET, "pending"),),
            cue=PAPER,
        ),
        _timed(
            "E16 Elevator empty",
            _after("elevator_empty"),
            (Mut("events.elevator", SET, True),),
            prose.BEATS["elevator_empty"],
            CHIME,
        ),
        Cond(
            "E17 Tension breaking",
            all_of(lt(SANITY, SANITY_BREAKING_BELOW), ne(TIER, "breaking"), ALWAYS),
            (Mut(TIER, SET, "breaking"),),
        ),
    ]


def timed_events() -> list[Cond]:
    return [*_early_events(), *_middle_events(), *_late_events()]
