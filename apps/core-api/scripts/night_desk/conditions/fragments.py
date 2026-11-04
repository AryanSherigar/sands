"""The fragment pipeline (group F): backstory evidence, one one-shot per fragment.

Each act has one slot. A gate fires only while its act's slot is empty, so a run
sees at most three fragments, the first one earned in each act; a fragment whose
act has passed is gone. The poster sits outside the slots.
"""

from scripts.night_desk import poster, prose, timeline
from scripts.night_desk.expr import (
    ALWAYS,
    SET,
    Cond,
    Expression,
    Mut,
    all_of,
    eq,
    gte,
    lt,
    window,
)

SHIFT = "shift_minutes"
ACT_WINDOWS: dict[str, Expression | tuple[Expression, ...]] = {
    "act1": lt(SHIFT, timeline.ACT2_START),
    "act2": window(SHIFT, timeline.ACT2_START, timeline.ACT3_START),
    "act3": gte(SHIFT, timeline.ACT3_START),
}
# Order is the preference when two gates open on the same turn.
FRAGMENTS: tuple[tuple[str, str, Expression], ...] = (
    ("f1", "act1", eq("visited.records_room", 1)),
    ("f4", "act1", eq("check.drawer", "yes")),
    ("f2", "act2", gte("visited.records_room", 2)),
    ("f3", "act2", eq("visited.print_room", True)),
    ("f6", "act3", eq("check.voicemail", "yes")),
    ("f5", "act3", eq("visited.cabin_14", True)),
)


def _fragment(order: int, fragment_id: str, slot: str, gate: Expression) -> Cond:
    return Cond(
        f"F{order:02d} Fragment {fragment_id}",
        all_of(gate, ACT_WINDOWS[slot], eq(f"fragments.{slot}", ""), ALWAYS),
        (Mut(f"fragments.{slot}", SET, fragment_id),),
        prose.FRAGMENT_EVIDENCE[fragment_id],
        is_one_shot=True,
    )


def _poster() -> Cond:
    return Cond(
        "FP Poster",
        all_of(
            eq("visited.elevator_lobby", True),
            eq("fragments.poster", "locked"),
            ALWAYS,
        ),
        (Mut("fragments.poster", SET, "shown"),),
        prose.FRAGMENT_EVIDENCE["poster"],
        is_one_shot=True,
        image_url=poster.poster_url(),
    )


def fragment_pipeline() -> list[Cond]:
    conditions = [
        _fragment(order, fragment_id, slot, gate)
        for order, (fragment_id, slot, gate) in enumerate(FRAGMENTS, start=1)
    ]
    return [*conditions, _poster()]
