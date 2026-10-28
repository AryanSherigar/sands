from app.engine.alliances.registry import alliance_between
from app.engine.coalitions.registry import is_member_against
from app.engine.movement.map_index import MapIndex
from app.engine.opinion import opinion_of
from app.engine.trait_axes import axis_totals
from app.models.world_state import WorldState
from strategy_contracts.coalition import CoalitionTuning
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis


def borders(
    world: WorldState, index: MapIndex, left_id: FactionId, right_id: FactionId
) -> bool:
    return any(
        world.regions[neighbor_id].owner_id == right_id
        for region_id, neighbors in index.neighbors.items()
        if world.regions[region_id].owner_id == left_id
        for neighbor_id in sorted(neighbors)
    )


def join_threshold(
    world: WorldState,
    scenario: StrategyScenario,
    tuning: CoalitionTuning,
    member_id: FactionId,
) -> int:
    leader = world.leaders[world.factions[member_id].leader_id]
    totals = axis_totals(leader, scenario)
    shift = tuning.caution_shift * totals.get(
        TraitAxis.CAUTION, 0
    ) - tuning.pride_shift * totals.get(TraitAxis.PRIDE, 0)
    return max(0, tuning.join_threat + shift)


def is_eligible_member(
    world: WorldState, member_id: FactionId, target_id: FactionId
) -> bool:
    member = world.factions[member_id]
    if member_id == target_id or member.is_destroyed or member.leader_id is None:
        return False
    return not is_member_against(world, member_id, target_id)


def would_join(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    member_id: FactionId,
    target_id: FactionId,
    threat: int,
) -> bool:
    tuning = scenario.tuning.coalition
    if not is_eligible_member(world, member_id, target_id):
        return False
    has_tie = (
        borders(world, index, member_id, target_id)
        or alliance_between(world, member_id, target_id) is not None
    )
    leader = world.leaders[world.factions[member_id].leader_id]
    target_leader_id = world.factions[target_id].leader_id
    is_resentful = opinion_of(leader, target_leader_id) < tuning.join_opinion_below
    return (
        has_tie
        and is_resentful
        and threat >= join_threshold(world, scenario, tuning, member_id)
    )
