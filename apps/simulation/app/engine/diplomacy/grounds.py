from collections import Counter

from app.engine.diplomacy.counters import next_counter
from app.engine.trait_axes import axis_totals
from app.models.world_character import LeaderState
from app.models.world_diplomacy import GroundState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.diplomacy import DiplomacyTuning, GroundKind
from strategy_contracts.ids import FactionId, LeaderId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

SLOW_FADE_AXES = (
    TraitAxis.AGGRESSION,
    TraitAxis.PRIDE,
    TraitAxis.ZEAL,
    TraitAxis.CRUELTY,
    TraitAxis.HONOR,
)
FAST_FADE_AXES = (TraitAxis.CAUTION, TraitAxis.TRUST, TraitAxis.GREED)
FIERCE_AXES = (TraitAxis.AGGRESSION, TraitAxis.PRIDE, TraitAxis.CRUELTY)
WARY_AXES = (TraitAxis.CAUTION, TraitAxis.TRUST)
PERSONAL_KINDS = frozenset(
    (GroundKind.INSULT, GroundKind.BROKEN_PROMISE, GroundKind.REFUSED_DEMAND)
)
FULL_PERCENT = 100


def _sum(totals: Counter[TraitAxis], axes: tuple[TraitAxis, ...]) -> int:
    return sum(totals[axis] for axis in axes)


def _clamp(value: int, low: int, high: int) -> int:
    return min(max(value, low), high)


def fade_per_turn(leader: LeaderState, scenario: StrategyScenario) -> int:
    tuning = scenario.tuning.diplomacy
    totals = axis_totals(leader, scenario)
    slow = _sum(totals, SLOW_FADE_AXES) // tuning.fade_axis_divisor
    fast = _sum(totals, FAST_FADE_AXES) // tuning.fade_axis_divisor
    return _clamp(tuning.fade_base - slow + fast, tuning.fade_min, tuning.fade_max)


def _is_wealthy_claim(
    world: WorldState, ground: GroundState, tuning: DiplomacyTuning
) -> bool:
    region = world.regions.get(ground.region_id or "")
    return (
        ground.kind == GroundKind.CLAIM
        and region is not None
        and region.wealth >= tuning.wealthy_region_wealth
    )


def act_threshold(
    ground: GroundState,
    leader: LeaderState,
    scenario: StrategyScenario,
    world: WorldState,
) -> int:
    tuning = scenario.tuning.diplomacy
    totals = axis_totals(leader, scenario)
    step = tuning.act_threshold_step
    value = tuning.act_threshold_base
    value += step * (_sum(totals, WARY_AXES) - _sum(totals, FIERCE_AXES))
    if ground.kind != GroundKind.CLAIM or ground.is_forged:
        value += step * totals[TraitAxis.HONOR]
    if ground.kind == GroundKind.HOLY_WAR:
        value -= step * totals[TraitAxis.ZEAL]
    if _is_wealthy_claim(world, ground, tuning):
        value -= step * totals[TraitAxis.GREED]
    return _clamp(value, tuning.act_threshold_min, tuning.act_threshold_max)


def _is_immature(ground: GroundState, turn: int) -> bool:
    return ground.matures_turn is not None and turn < ground.matures_turn


def current_strength(
    ground: GroundState, leader: LeaderState, scenario: StrategyScenario, turn: int
) -> int:
    if _is_immature(ground, turn):
        return 0
    faded = fade_per_turn(leader, scenario) * (turn - ground.since_turn)
    return max(0, ground.strength - faded)


def is_usable(
    world: WorldState, scenario: StrategyScenario, ground: GroundState
) -> bool:
    faction = world.factions.get(ground.holder_faction_id)
    leader = world.leaders.get(ground.holder_leader_id)
    if faction is None or faction.is_destroyed or leader is None:
        return False
    if not leader.is_alive or faction.leader_id != ground.holder_leader_id:
        return False
    strength = current_strength(ground, leader, scenario, world.clock.turn)
    return strength >= act_threshold(ground, leader, scenario, world)


def _find_ground(
    world: WorldState,
    holder_faction_id: FactionId,
    target_faction_id: FactionId,
    kind: GroundKind,
    region_id: RegionId | None,
) -> GroundState | None:
    return next(
        (
            ground
            for ground in world.grounds
            if (ground.holder_faction_id, ground.target_faction_id, ground.kind)
            == (holder_faction_id, target_faction_id, kind)
            and ground.region_id == region_id
        ),
        None,
    )


def grant_ground(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    kind: GroundKind,
    holder_faction_id: FactionId,
    target_faction_id: FactionId,
    region_id: RegionId | None = None,
    strength: int | None = None,
) -> GroundState:
    leader_id = world.factions[holder_faction_id].leader_id
    if leader_id is None:
        raise ValueError("a ground needs a living holder leader")
    amount = strength
    if amount is None:
        amount = scenario.tuning.diplomacy.ground_base_strength[kind]
    existing = _find_ground(
        world, holder_faction_id, target_faction_id, kind, region_id
    )
    if existing is not None:
        existing.strength = amount
        existing.since_turn = world.clock.turn
        existing.holder_leader_id = leader_id
        return existing
    ground = GroundState(
        id=f"ground_{next_counter(world, CounterKind.GROUND)}",
        kind=kind,
        holder_faction_id=holder_faction_id,
        holder_leader_id=leader_id,
        target_faction_id=target_faction_id,
        region_id=region_id,
        strength=amount,
        since_turn=world.clock.turn,
        is_personal=kind in PERSONAL_KINDS,
    )
    world.grounds.append(ground)
    return ground


def _insult_strength_this_turn(world: WorldState, holder_faction_id: FactionId) -> int:
    return sum(
        ground.strength
        for ground in world.grounds
        if ground.kind == GroundKind.INSULT
        and ground.holder_faction_id == holder_faction_id
        and ground.since_turn == world.clock.turn
    )


def grant_insult_ground(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    holder_faction_id: FactionId,
    target_faction_id: FactionId,
    grade: int,
) -> GroundState | None:
    tuning = scenario.tuning.diplomacy
    bounded = _clamp(grade, 0, tuning.max_insult_grade)
    room = tuning.insult_strength_cap_per_turn - _insult_strength_this_turn(
        world, holder_faction_id
    )
    amount = min(bounded * tuning.ground_base_strength[GroundKind.INSULT], room)
    if amount <= 0:
        return None
    return grant_ground(
        world,
        scenario,
        kind=GroundKind.INSULT,
        holder_faction_id=holder_faction_id,
        target_faction_id=target_faction_id,
        strength=amount,
    )


def inherit_grounds(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    new_leader_id: LeaderId,
) -> None:
    tuning = scenario.tuning.diplomacy
    turn = world.clock.turn
    for ground in world.grounds:
        if ground.holder_faction_id != faction_id:
            continue
        previous = world.leaders.get(ground.holder_leader_id)
        remaining = ground.strength
        if previous is not None:
            remaining = current_strength(ground, previous, scenario, turn)
        percent = tuning.heir_claim_percent
        if ground.is_personal:
            percent = tuning.heir_insult_percent
        ground.strength = remaining * percent // FULL_PERCENT
        ground.since_turn = turn
        ground.holder_leader_id = new_leader_id


def _is_spent(
    world: WorldState, scenario: StrategyScenario, ground: GroundState
) -> bool:
    leader = world.leaders.get(ground.holder_leader_id)
    if leader is None:
        return True
    turn = world.clock.turn
    if _is_immature(ground, turn):
        return False
    return current_strength(ground, leader, scenario, turn) == 0


def expire_grounds(world: WorldState, scenario: StrategyScenario) -> list[GroundState]:
    removed = [ground for ground in world.grounds if _is_spent(world, scenario, ground)]
    world.grounds = [ground for ground in world.grounds if ground not in removed]
    return removed


def forgive(
    world: WorldState,
    scenario: StrategyScenario,
    holder_faction_id: FactionId,
    target_faction_id: FactionId,
    amount: int,
) -> None:
    for ground in world.grounds:
        if (ground.holder_faction_id, ground.target_faction_id) == (
            holder_faction_id,
            target_faction_id,
        ):
            ground.strength = max(0, ground.strength - amount)


def seed_claim_grounds(world: WorldState, scenario: StrategyScenario) -> None:
    for region_id in sorted(world.regions):
        region = world.regions[region_id]
        for claimant_id in sorted(region.claimant_ids):
            if region.owner_id in (None, claimant_id):
                continue
            if world.factions[claimant_id].leader_id is None:
                continue
            grant_ground(
                world,
                scenario,
                kind=GroundKind.CLAIM,
                holder_faction_id=claimant_id,
                target_faction_id=region.owner_id,
                region_id=region_id,
            )
