from dataclasses import dataclass

from app.models.world_state import WorldState
from strategy_contracts.conditions import ConditionScope


@dataclass(frozen=True)
class Subject:
    kind: ConditionScope
    id: str


def related_entity_id(
    world: WorldState, subject: Subject, wanted: ConditionScope
) -> str | None:
    """The id of the ``wanted`` entity tied to ``subject``, or None if there is none."""
    if subject.kind is wanted:
        return subject.id
    resolve = _RELATIONS.get((subject.kind, wanted))
    return resolve(world, subject.id) if resolve is not None else None


def _governor_of_region(world: WorldState, region_id: str) -> str | None:
    region = world.regions.get(region_id)
    return region.governor_id if region is not None else None


def _region_of_governor(world: WorldState, governor_id: str) -> str | None:
    governor = world.governors.get(governor_id)
    return governor.region_id if governor is not None else None


def _region_of_army(world: WorldState, army_id: str) -> str | None:
    army = world.armies.get(army_id)
    return army.location_id if army is not None else None


_RELATIONS = {
    (ConditionScope.REGION, ConditionScope.GOVERNOR): _governor_of_region,
    (ConditionScope.GOVERNOR, ConditionScope.REGION): _region_of_governor,
    (ConditionScope.ARMY, ConditionScope.REGION): _region_of_army,
}
