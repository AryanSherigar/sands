"""Labels, paths and helpers shared by every condition group."""

from scripts.seeding.expr import SET, Expression, Mut, eq
from scripts.zegaris.ids import entity_ref
from scripts.zegaris.schema import NO_VALUE

GROUP_ORDER = ("T", "A", "R")
TITHE = "world.tithe"
ACCESS = "world.access"
TITHE_STEP = "intent.tithe_step"
ACCESS_STEP = "intent.access_step"
RETRIEVAL = "quests.retrieval.stage"


def label(group: str, index: int, text: str) -> str:
    return f"{group}{index:02d} {text}"


def at(location_slug: str) -> Expression:
    return eq("current_location_id", entity_ref(location_slug))


def clear(path: str) -> Mut:
    return Mut(path, SET, NO_VALUE)
