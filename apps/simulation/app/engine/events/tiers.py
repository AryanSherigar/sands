from app.engine.conditions import evaluate
from app.engine.subjects import Subject
from app.models.world_state import WorldState
from strategy_contracts.events import EventDefinition


def tier_level(
    world: WorldState,
    template: EventDefinition,
    subject: Subject,
    *,
    scar: int,
    faction_id: str,
) -> int:
    """The severity level the subject is judged at, 0 when no tier holds.

    A scar raises the judged tier by one rung per ``points_per_tier_bump``.
    """
    index = _highest_holding_index(world, template, subject, faction_id)
    if index is None:
        return 0
    bump = scar // template.scar.points_per_tier_bump
    return template.tiers[min(index + bump, len(template.tiers) - 1)].level


def _highest_holding_index(
    world: WorldState, template: EventDefinition, subject: Subject, faction_id: str
) -> int | None:
    for index in range(len(template.tiers) - 1, -1, -1):
        trigger = template.tiers[index].trigger
        if evaluate(world, trigger, faction_id=faction_id, subject=subject):
            return index
    return None
