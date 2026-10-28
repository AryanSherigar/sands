from dataclasses import dataclass

from app.engine.ai.candidates import Candidate
from app.engine.ai.knowledge import (
    Knowledge,
    build_knowledge,
    known_foreign_armies,
    region_distances,
)
from app.engine.ai.situation import war_enemies
from app.models.orders import AttackOrder, MoveArmyOrder
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

MAX_ATTACK_TARGETS = 2
UNREACHABLE = 10**6


@dataclass(frozen=True)
class MovementContext:
    world: WorldState
    scenario: StrategyScenario
    faction_id: FactionId
    knowledge: Knowledge
    idle: list[ArmyState]
    enemies: frozenset[FactionId]


def build_movement_context(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> MovementContext:
    idle = [
        army
        for _, army in sorted(world.armies.items())
        if army.owner_id == faction_id and army.march is None
    ]
    return MovementContext(
        world,
        scenario,
        faction_id,
        build_knowledge(world, scenario, faction_id),
        idle,
        frozenset(war_enemies(world, faction_id)),
    )


def _move(ctx: MovementContext, army: ArmyState, region_id: RegionId) -> MoveArmyOrder:
    return MoveArmyOrder(
        faction_id=ctx.faction_id, army_id=army.id, to_region_id=region_id
    )


def _enemy_regions(ctx: MovementContext) -> list[RegionId]:
    owned = [
        region_id
        for region_id, owner_id in ctx.knowledge.owners.items()
        if owner_id in ctx.enemies
    ]
    return sorted(
        owned,
        key=lambda region_id: (ctx.knowledge.garrisons.get(region_id, 0), region_id),
    )


def _strike_candidates(ctx: MovementContext) -> list[Candidate]:
    tuning = ctx.scenario.tuning.ai
    targets = _enemy_regions(ctx)
    candidates: list[Candidate] = []
    for army in ctx.idle:
        neighbors = ctx.knowledge.index.neighbors.get(army.location_id, frozenset())
        adjacent = [region_id for region_id in targets if region_id in neighbors]
        for region_id in adjacent[:MAX_ATTACK_TARGETS]:
            is_strong = sum(army.troops.values()) >= ctx.knowledge.garrisons.get(
                region_id, 0
            )
            base = tuning.strike_bonus if is_strong else -tuning.risk_penalty
            order = AttackOrder(
                faction_id=ctx.faction_id, army_id=army.id, target_region_id=region_id
            )
            candidates.append(Candidate(order, ScoreCategory.ATTACK, base))
        if not adjacent:
            candidates.extend(_approach(ctx, army, targets))
    return candidates


def _approach(
    ctx: MovementContext, army: ArmyState, targets: list[RegionId]
) -> list[Candidate]:
    if not targets:
        return []
    distances = region_distances(ctx.knowledge.index, army.location_id)
    nearest = min(
        targets,
        key=lambda region_id: (distances.get(region_id, UNREACHABLE), region_id),
    )
    if nearest not in distances:
        return []
    base = ctx.scenario.tuning.ai.approach_bonus
    return [Candidate(_move(ctx, army, nearest), ScoreCategory.ATTACK, base)]


def _border_regions(ctx: MovementContext, target_id: FactionId) -> list[RegionId]:
    index = ctx.knowledge.index
    return sorted(
        region_id
        for region_id, region in ctx.world.regions.items()
        if region.owner_id == ctx.faction_id
        and any(
            ctx.knowledge.owners.get(neighbor) == target_id
            for neighbor in index.neighbors.get(region_id, frozenset())
        )
    )


def _stage_candidates(ctx: MovementContext) -> list[Candidate]:
    aim = ctx.world.aims.get(ctx.faction_id)
    if aim is None or aim.category != ScoreCategory.ATTACK:
        return []
    if aim.target_faction_id is None or aim.target_faction_id in ctx.enemies:
        return []
    border = _border_regions(ctx, aim.target_faction_id)
    candidates: list[Candidate] = []
    for army in ctx.idle:
        if army.location_id in border or not border:
            continue
        distances = region_distances(ctx.knowledge.index, army.location_id)
        reachable = [region_id for region_id in border if region_id in distances]
        if reachable:
            nearest = min(
                reachable, key=lambda region_id: (distances[region_id], region_id)
            )
            base = ctx.scenario.tuning.ai.approach_bonus
            candidates.append(
                Candidate(_move(ctx, army, nearest), ScoreCategory.ATTACK, base)
            )
    return candidates


def _threatened_regions(ctx: MovementContext) -> list[RegionId]:
    index = ctx.knowledge.index
    hostile = {
        army.location_id
        for army in known_foreign_armies(ctx.world, ctx.faction_id, ctx.knowledge)
        if army.owner_id in ctx.enemies
    }
    return sorted(
        region_id
        for region_id, region in ctx.world.regions.items()
        if region.owner_id == ctx.faction_id
        and (
            region_id in hostile
            or hostile & index.neighbors.get(region_id, frozenset())
        )
    )


def _defense_candidates(ctx: MovementContext) -> list[Candidate]:
    base = ctx.scenario.tuning.ai.defense_bonus
    occupied = {army.location_id for army in ctx.idle}
    candidates: list[Candidate] = []
    for region_id in _threatened_regions(ctx):
        if region_id in occupied:
            continue
        ranked = sorted(
            (
                region_distances(ctx.knowledge.index, army.location_id).get(
                    region_id, UNREACHABLE
                ),
                army.id,
            )
            for army in ctx.idle
        )
        if ranked and ranked[0][0] < UNREACHABLE:
            army = ctx.world.armies[ranked[0][1]]
            candidates.append(
                Candidate(_move(ctx, army, region_id), ScoreCategory.BUILD, base)
            )
    return candidates


def _expand_candidates(ctx: MovementContext) -> list[Candidate]:
    candidates: list[Candidate] = []
    for army in ctx.idle:
        neighbors = ctx.knowledge.index.neighbors.get(army.location_id, frozenset())
        neutral = [
            region_id
            for region_id in sorted(neighbors)
            if region_id in ctx.knowledge.owners
            and ctx.knowledge.owners[region_id] is None
        ]
        if neutral:
            candidates.append(
                Candidate(_move(ctx, army, neutral[0]), ScoreCategory.EXPAND)
            )
    return candidates


def movement_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    ctx = build_movement_context(world, scenario, faction_id)
    return (
        _strike_candidates(ctx)
        + _stage_candidates(ctx)
        + _defense_candidates(ctx)
        + _expand_candidates(ctx)
    )
