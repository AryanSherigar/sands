from collections.abc import Callable

from app.engine.negotiation import player_faction_id
from app.engine.subjects import Subject, related_entity_id
from app.exceptions.condition_exceptions import UnsupportedMetricError
from app.models.world_faction import FactionState
from app.models.world_state import WorldState
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    AllOf,
    Comparison,
    Condition,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
    Negation,
    metric_scope,
)

FactionReader = Callable[[WorldState, FactionState, Comparison], int]
EntityReader = Callable[[WorldState, str], int]

_COMPARATORS: dict[ConditionOperator, Callable[[int, int], bool]] = {
    ConditionOperator.LT: lambda left, right: left < right,
    ConditionOperator.LTE: lambda left, right: left <= right,
    ConditionOperator.EQ: lambda left, right: left == right,
    ConditionOperator.GTE: lambda left, right: left >= right,
    ConditionOperator.GT: lambda left, right: left > right,
}


def _count_owned_regions(world: WorldState, faction: FactionState) -> int:
    return sum(1 for region in world.regions.values() if region.owner_id == faction.id)


def _count_regions_in_unrest(
    world: WorldState, faction: FactionState, comparison: Comparison
) -> int:
    threshold = comparison.threshold or 0
    return sum(
        1
        for region in world.regions.values()
        if region.owner_id == faction.id and region.unrest >= threshold
    )


FACTION_READERS: dict[ConditionMetric, FactionReader] = {
    ConditionMetric.TURN: lambda world, _, __: world.clock.turn,
    ConditionMetric.TREASURY: lambda _, faction, __: faction.treasury,
    ConditionMetric.STABILITY: lambda _, faction, __: faction.stability,
    ConditionMetric.WAR_EXHAUSTION: lambda _, faction, __: faction.war_exhaustion,
    ConditionMetric.REGION_COUNT: lambda world, faction, _: _count_owned_regions(
        world, faction
    ),
    ConditionMetric.IS_FACTION_DESTROYED: lambda _, faction, __: int(
        faction.is_destroyed
    ),
    ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST: _count_regions_in_unrest,
}
ENTITY_READERS: dict[ConditionMetric, EntityReader] = {
    ConditionMetric.REGION_UNREST: lambda world, entity_id: (
        world.regions[entity_id].unrest
    ),
    ConditionMetric.GOVERNOR_OPINION: lambda world, entity_id: (
        world.governors[entity_id].opinion_of_ruler
    ),
    ConditionMetric.ARMY_UNPAID_TURNS: lambda world, entity_id: (
        world.armies[entity_id].unpaid_turns
    ),
    ConditionMetric.ARMY_MORALE: lambda world, entity_id: (
        world.armies[entity_id].morale
    ),
}
_ENTITY_TABLES = {
    ConditionScope.REGION: "regions",
    ConditionScope.GOVERNOR: "governors",
    ConditionScope.ARMY: "armies",
}


def _resolve_faction(
    world: WorldState,
    comparison: Comparison,
    faction_id: str | None,
    subject: Subject | None,
) -> FactionState:
    target_id = comparison.subject_id or faction_id or player_faction_id(world)
    if target_id == SUBJECT_PLACEHOLDER:
        target_id = _require_subject(subject, ConditionScope.FACTION).id
    faction = world.factions.get(target_id)
    if faction is None:
        raise UnsupportedMetricError(f"condition names unknown faction {target_id}")
    return faction


def _require_subject(subject: Subject | None, kind: ConditionScope) -> Subject:
    if subject is None or subject.kind is not kind:
        raise UnsupportedMetricError(f"condition needs a {kind.value} subject")
    return subject


def _resolve_entity_id(
    world: WorldState,
    comparison: Comparison,
    scope: ConditionScope,
    subject: Subject | None,
) -> str | None:
    if comparison.subject_id is None:
        raise UnsupportedMetricError(f"{comparison.metric.value} needs a subject")
    if comparison.subject_id != SUBJECT_PLACEHOLDER:
        return comparison.subject_id
    if subject is None:
        raise UnsupportedMetricError(f"{comparison.metric.value} needs a subject")
    return related_entity_id(world, subject, scope)


def _read_entity_metric(
    world: WorldState, comparison: Comparison, subject: Subject | None
) -> int | None:
    reader = ENTITY_READERS[comparison.metric]
    entity_id = _resolve_entity_id(
        world, comparison, metric_scope(comparison.metric), subject
    )
    table = getattr(world, _ENTITY_TABLES[metric_scope(comparison.metric)])
    if entity_id is None or entity_id not in table:
        return None
    return reader(world, entity_id)


def read_metric(
    world: WorldState,
    comparison: Comparison,
    *,
    faction_id: str | None = None,
    subject: Subject | None = None,
) -> int | None:
    """The metric's value, or None when the subject has no such entity."""
    if comparison.metric in ENTITY_READERS:
        return _read_entity_metric(world, comparison, subject)
    reader = FACTION_READERS.get(comparison.metric)
    if reader is None:
        raise UnsupportedMetricError(
            f"condition metric {comparison.metric.value} has no reader"
        )
    faction = _resolve_faction(world, comparison, faction_id, subject)
    return reader(world, faction, comparison)


def evaluate(
    world: WorldState,
    condition: Condition,
    *,
    faction_id: str | None = None,
    subject: Subject | None = None,
) -> bool:
    if isinstance(condition, Comparison):
        value = read_metric(world, condition, faction_id=faction_id, subject=subject)
        if value is None:
            return False
        return _COMPARATORS[condition.operator](value, condition.value)
    if isinstance(condition, Negation):
        return not evaluate(
            world, condition.condition, faction_id=faction_id, subject=subject
        )
    results = (
        evaluate(world, child, faction_id=faction_id, subject=subject)
        for child in condition.conditions
    )
    return all(results) if isinstance(condition, AllOf) else any(results)
