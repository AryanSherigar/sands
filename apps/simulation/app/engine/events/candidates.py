from app.engine.subjects import Subject
from app.models.world_state import WorldState
from strategy_contracts.conditions import ConditionScope


def list_subjects(
    world: WorldState, kind: ConditionScope, faction_id: str
) -> list[Subject]:
    """Subjects of ``kind`` that belong to the faction, sorted by id."""
    ids = _OWNED_IDS[kind](world, faction_id)
    return [Subject(kind, subject_id) for subject_id in sorted(ids)]


def _owned_region_ids(world: WorldState, faction_id: str) -> list[str]:
    return [
        region.id for region in world.regions.values() if region.owner_id == faction_id
    ]


def _owned_governor_ids(world: WorldState, faction_id: str) -> list[str]:
    owned = set(_owned_region_ids(world, faction_id))
    return [
        governor.id
        for governor in world.governors.values()
        if governor.region_id in owned
    ]


def _owned_army_ids(world: WorldState, faction_id: str) -> list[str]:
    return [army.id for army in world.armies.values() if army.owner_id == faction_id]


def _faction_ids(world: WorldState, faction_id: str) -> list[str]:
    return [faction_id] if faction_id in world.factions else []


_OWNED_IDS = {
    ConditionScope.REGION: _owned_region_ids,
    ConditionScope.GOVERNOR: _owned_governor_ids,
    ConditionScope.ARMY: _owned_army_ids,
    ConditionScope.FACTION: _faction_ids,
}
