"""Group A: record that a character has been appraised.

The narrator gives the stat block in the same turn it sets the flag; this
condition only keeps the bookkeeping and clears the flag.
"""

from scripts.reincarnated_aristocrat.characters import CHARACTER_SLUGS
from scripts.reincarnated_aristocrat.conditions.common import attr, clear, label
from scripts.seeding.expr import SET, Cond, Mut, eq


def appraisal_conditions() -> list[Cond]:
    return [
        Cond(
            label("A", index, f"Appraised {slug}"),
            eq("intent.appraise_target", slug),
            (Mut(attr(slug, "is_appraised"), SET, True), *clear("appraise_target")),
        )
        for index, slug in enumerate(CHARACTER_SLUGS, start=1)
    ]
