"""Narrator facts (group N): restrictions repeated in the late facts block, where
a small model weighs them more than in the persona."""

from scripts.night_desk import prose
from scripts.night_desk.expr import Cond, gte

SHIFT = "shift_minutes"


def never_describe() -> list[Cond]:
    return [
        Cond(f"N0{number} Never describe", gte(SHIFT, 0), (), text, is_fact=True)
        for number, text in enumerate(prose.NEVER_DESCRIBE, start=1)
    ]
