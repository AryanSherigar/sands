"""Group A: Zegarian access, enforced softly through narrator consequences.

Map edges are advisory by product decision, so these conditions do not block
movement. They tell the narrator what the city does about a player standing
where they should not.
"""

from scripts.seeding.expr import SET, Cond, Mut, all_of, eq, ne
from scripts.zegaris.conditions.common import (
    ACCESS,
    ACCESS_STEP,
    TITHE,
    at,
    clear,
    label,
)

BADGE_TEXT = (
    "A Zegarian notary or Templar issues the player a worker's badge. Show it "
    "pinned to the player's clothes. It lets a bonded outlander work in the "
    "Flaxen Wards and nothing more."
)
ESCORT_TEXT = (
    "The player walks behind a Zegarian master. Outsiders are permitted on the "
    "higher terraces only in this posture; keep a respectful pace behind."
)
REVOKED_TEXT = "The player's right to be in Zegaris is withdrawn. The badge is taken."
GATE_TEXT = (
    "The player stands at the Gate without a badge or master. The Black "
    "Templars bar the way in silence. A hired outlander may be badged; "
    "otherwise the player is turned back without violence."
)
WARDS_TEXT = (
    "The player is in the Flaxen Wards without a badge or master. Citizens "
    "notice and keep their distance; Templars arrive and escort the player "
    "back to the Gate. They do not strike an outsider who does not resist."
)
PROMENADE_TEXT = (
    "Outsiders are strictly forbidden on the Amber Promenade unless they walk "
    "behind a master. Without that, Black Templars intercept the player and "
    "return them to the lower wards. A strike against a Zegarian makes the "
    "player a slave."
)
CROWN_TEXT = (
    "The Golden Crown is closed to outsiders. White Templars stop the player "
    "at the cathedral steps; do not allow entry or any look at the icon's "
    "inner vault."
)


def _grant(index: int, step: str, level: str, text: str) -> Cond:
    return Cond(
        label("A", index, f"access {level}"),
        all_of(eq(ACCESS_STEP, step), ne(ACCESS, level)),
        (Mut(ACCESS, SET, level), clear(ACCESS_STEP)),
        text,
    )


def _gate(index: int, slug: str, text: str, level: str) -> Cond:
    return Cond(
        label("A", index, f"{slug} without {level}"),
        all_of(at(slug), eq(ACCESS, "none"), ne(TITHE, "aftermath")),
        (),
        text,
        is_fact=True,
    )


def access_conditions() -> list[Cond]:
    return [
        _grant(1, "badge", "badge", BADGE_TEXT),
        _grant(2, "escort", "escort", ESCORT_TEXT),
        Cond(
            label("A", 3, "revoked"),
            eq(ACCESS_STEP, "revoked"),
            (Mut(ACCESS, SET, "none"), clear(ACCESS_STEP)),
            REVOKED_TEXT,
        ),
        _gate(4, "gate_of_the_unsworn", GATE_TEXT, "badge"),
        _gate(5, "flaxen_wards", WARDS_TEXT, "badge"),
        Cond(
            label("A", 6, "promenade without escort"),
            all_of(at("amber_promenade"), ne(ACCESS, "escort"), ne(TITHE, "aftermath")),
            (),
            PROMENADE_TEXT,
            is_fact=True,
        ),
        Cond(
            label("A", 7, "crown without escort"),
            all_of(at("golden_crown"), ne(ACCESS, "escort"), ne(TITHE, "aftermath")),
            (),
            CROWN_TEXT,
            is_fact=True,
        ),
        Cond(
            label("A", 8, "discard unknown step"),
            ne(ACCESS_STEP, ""),
            (clear(ACCESS_STEP),),
            "",
        ),
    ]
