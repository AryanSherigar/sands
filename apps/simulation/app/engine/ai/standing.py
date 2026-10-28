from app.engine.ai.knowledge import build_knowledge, known_foreign_armies
from app.engine.alliances.registry import alliance_between
from app.engine.vassals.registry import vassalage_between
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import NonAggressionTerm

FULL_PERCENT = 100


def _pair(first: FactionId, second: FactionId) -> frozenset[FactionId]:
    return frozenset((first, second))


def _has_alliance_relation(world: WorldState, pair: frozenset[FactionId]) -> bool:
    return any(
        _pair(relation.faction_a, relation.faction_b) == pair
        and relation.status == RelationStatus.ALLIANCE
        for relation in world.relations
    )


def is_bound(world: WorldState, first: FactionId, second: FactionId) -> bool:
    pair = _pair(first, second)
    if any(_pair(truce.faction_a, truce.faction_b) == pair for truce in world.truces):
        return True
    if alliance_between(world, first, second) is not None:
        return True
    if world.alliance_ruleset < 1 and _has_alliance_relation(world, pair):
        return True
    if vassalage_between(world, first, second) is not None:
        return True
    return any(
        isinstance(item.term, NonAggressionTerm)
        and item.status == CommitmentStatus.ACTIVE
        and _pair(item.term.faction_a, item.term.faction_b) == pair
        for item in world.commitments
    )


def _own_troops(world: WorldState, faction_id: FactionId) -> int:
    return sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == faction_id
    )


def known_power_ratio(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    target_id: FactionId,
) -> int:
    knowledge = build_knowledge(world, scenario, faction_id)
    garrisons = sum(
        knowledge.garrisons.get(region_id, 0)
        for region_id, owner_id in knowledge.owners.items()
        if owner_id == target_id
    )
    field_armies = sum(
        sum(army.troops.values())
        for army in known_foreign_armies(world, faction_id, knowledge)
        if army.owner_id == target_id
    )
    known = garrisons + field_armies
    if known == 0:
        return FULL_PERCENT
    return FULL_PERCENT * _own_troops(world, faction_id) // known
