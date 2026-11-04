"""Rule invariants (data doc §11): mechanical backstops enforced on every mutation."""

from app.models.invariant import InvariantCreate
from scripts.night_desk import schema
from scripts.night_desk.expr import leaf


def invariants() -> list[InvariantCreate]:
    return [
        InvariantCreate(
            label="Sanity cap",
            invariant_expression=leaf("sanity", "<=", schema.SANITY_CEILING),
            applies_to="player",
            narrator_text="Composure cannot be restored beyond what it was at the start of the night.",
        ),
        InvariantCreate(
            label="Clock bound",
            invariant_expression=leaf("shift_minutes", "<=", schema.SHIFT_MINUTES_MAX),
            applies_to="global",
            narrator_text="The night ends at dawn.",
        ),
        InvariantCreate(
            label="Unsigned counts",
            invariant_expression=leaf("count.unsigned", "<=", schema.UNSIGNED_MAX),
            applies_to="global",
            narrator_text="There are only three counts in a night.",
        ),
    ]
