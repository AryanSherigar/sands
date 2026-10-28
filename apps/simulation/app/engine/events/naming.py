from app.engine.subjects import Subject
from app.models.world_state import WorldState
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.scenario import StrategyScenario


def subject_name(
    world: WorldState, scenario: StrategyScenario, subject: Subject
) -> str:
    if subject.kind is ConditionScope.REGION:
        regions = {region.id: region.name for region in scenario.map.regions}
        return regions.get(subject.id, subject.id)
    if subject.kind is ConditionScope.GOVERNOR:
        governor = world.governors.get(subject.id)
        return governor.name if governor is not None else subject.id
    if subject.kind is ConditionScope.FACTION:
        names = {faction.id: faction.name for faction in scenario.factions}
        return names.get(subject.id, subject.id)
    return subject.id
