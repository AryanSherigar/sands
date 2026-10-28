from app.engine.ai.candidates import Candidate
from app.engine.ai.generators.movement import (
    UNREACHABLE,
    MovementContext,
    build_movement_context,
)
from app.engine.ai.knowledge import region_distances
from app.engine.trait_axes import axis_totals
from app.models.orders import MoveArmyOrder
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.traits import TraitAxis


def _is_cunning(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    leader_id = world.factions[faction_id].leader_id
    if leader_id is None or leader_id not in world.leaders:
        return False
    totals = axis_totals(world.leaders[leader_id], scenario)
    return totals[TraitAxis.CUNNING] >= scenario.tuning.ai.feint_min_cunning


def _target_regions(ctx: MovementContext, target_id: FactionId) -> list[RegionId]:
    return sorted(
        (
            region_id
            for region_id, owner_id in ctx.knowledge.owners.items()
            if owner_id == target_id
        ),
        key=lambda region_id: (ctx.knowledge.garrisons.get(region_id, 0), region_id),
    )


def _decoy_region(ctx: MovementContext, targets: list[RegionId]) -> RegionId | None:
    distances = region_distances(ctx.knowledge.index, targets[0])
    reachable = [region_id for region_id in targets[1:] if region_id in distances]
    if not reachable:
        return None
    return max(
        reachable,
        key=lambda region_id: (distances.get(region_id, UNREACHABLE), region_id),
    )


def feint_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    aim = world.aims.get(faction_id)
    if (
        aim is None
        or aim.category != ScoreCategory.ATTACK
        or aim.target_faction_id is None
    ):
        return []
    ctx = build_movement_context(world, scenario, faction_id)
    if aim.target_faction_id not in ctx.enemies or len(ctx.idle) < 2:
        return []
    if not _is_cunning(world, scenario, faction_id):
        return []
    targets = _target_regions(ctx, aim.target_faction_id)
    decoy_region = _decoy_region(ctx, targets) if len(targets) >= 2 else None
    if decoy_region is None:
        return []
    ranked = sorted(ctx.idle, key=lambda army: (-sum(army.troops.values()), army.id))
    base = scenario.tuning.ai.feint_bonus
    return [
        Candidate(
            _move_order(ctx, ranked[0].id, targets[0]), ScoreCategory.ATTACK, base
        ),
        Candidate(
            _move_order(ctx, ranked[-1].id, decoy_region), ScoreCategory.ATTACK, base
        ),
    ]


def _move_order(
    ctx: MovementContext, army_id: str, region_id: RegionId
) -> MoveArmyOrder:
    return MoveArmyOrder(
        faction_id=ctx.faction_id, army_id=army_id, to_region_id=region_id
    )
