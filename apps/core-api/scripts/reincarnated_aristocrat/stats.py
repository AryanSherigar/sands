"""The appraisal stat vocabulary and the hidden-cap formula.

Names follow the web novel's Appraisal block (chapter 2). Courage is not in
that block; the owner kept it as an extra stat.
"""

from dataclasses import dataclass

from app.models.entity import AttributeFieldSchema

STAT_KEYS = ("leadership", "prowess", "ingenuity", "politics", "courage", "ambition")
TRAINABLE_STATS = ("leadership", "prowess", "ingenuity", "politics")
STAT_LABELS = {
    "leadership": "Leadership",
    "prowess": "Prowess",
    "ingenuity": "Ingenuity",
    "politics": "Politics",
    "courage": "Courage",
    "ambition": "Ambition",
}
APTITUDE_KEYS = (
    "infantry",
    "cavalry",
    "archers",
    "magic_troops",
    "fortification",
    "weapons",
    "navy",
    "air",
    "stratagem",
)
APTITUDE_LABELS = {
    "infantry": "Infantry",
    "cavalry": "Cavalry",
    "archers": "Archers",
    "magic_troops": "Magic troops",
    "fortification": "Fortification",
    "weapons": "Weapons",
    "navy": "Navy",
    "air": "Air",
    "stratagem": "Stratagem",
}
RANKS = ("E", "D", "C", "B", "A", "S")

STAT_FLOOR = 0
STAT_CEILING = 120
PERCENT_CEILING = 100
CHILD_HEADROOM_RATIO = 0.5
CHILD_HEADROOM_MINIMUM = 10
ADULT_HEADROOM_RATIO = 0.15
ADULT_HEADROOM_MINIMUM = 5
INITIAL_LOYALTY = 40

UNCAPPED_STATS = ("ambition",)


@dataclass(frozen=True)
class StatSpec:
    start: int
    wiki_cap: int | None = None


def derive_cap(start: int, is_adult: bool) -> int:
    """Room to grow above the starting value, hidden from the player."""
    ratio = ADULT_HEADROOM_RATIO if is_adult else CHILD_HEADROOM_RATIO
    minimum = ADULT_HEADROOM_MINIMUM if is_adult else CHILD_HEADROOM_MINIMUM
    return min(STAT_CEILING, start + max(minimum, round(start * ratio)))


def stat_cap(key: str, spec: StatSpec, is_adult: bool) -> int:
    if key in UNCAPPED_STATS:
        return PERCENT_CEILING
    if spec.wiki_cap is not None:
        return spec.wiki_cap
    return derive_cap(spec.start, is_adult)


def stat_field(
    key: str, spec: StatSpec, is_adult: bool
) -> tuple[str, AttributeFieldSchema]:
    return key, AttributeFieldSchema(
        type="number",
        initial=spec.start,
        min=STAT_FLOOR,
        max=stat_cap(key, spec, is_adult),
        label=STAT_LABELS[key],
        is_narrator_visible=True,
    )
