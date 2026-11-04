"""Night Desk's condition DSL: the shared builders plus its clock-reading ALWAYS."""

from scripts.seeding.expr import (  # noqa: F401
    AND,
    DECREMENT,
    FACTS_PLACEMENT,
    INCREMENT,
    OR,
    SET,
    Cond,
    Cue,
    Expression,
    Mut,
    all_of,
    either,
    eq,
    gt,
    gte,
    is_in,
    leaf,
    lt,
    ne,
    to_condition,
    to_state_mutations,
    window,
)

# NOTE: the evaluator skips a condition unless a path it reads changed last turn.
# The clock changes every turn, so ALWAYS makes a condition read it and run on the
# same turn as a check answer or a move.
ALWAYS = gte("shift_minutes", 0)
