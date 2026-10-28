from app.engine.ai.candidates import Candidate
from app.engine.ai.knowledge import build_knowledge
from app.engine.ai.situation import war_enemies
from app.engine.ai.standing import is_bound, known_power_ratio
from app.engine.diplomacy.grounds import current_strength, is_usable
from app.engine.trait_axes import axis_totals
from app.models.orders import (
    CallNegotiationOrder,
    DeclareWarOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
)
from app.models.world_diplomacy import GroundState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm
from strategy_contracts.traits import TraitAxis

FULL_PERCENT = 100
RATIO_SWING_CAP = 8
STRENGTH_POINTS_CAP = 10
CUNNING_POINTS_CAP = 4


def _clamp(value: int, low: int, high: int) -> int:
    return min(max(value, low), high)


def _eligible_targets(
    world: WorldState, faction_id: FactionId, *, include_player: bool
) -> list[FactionId]:
    enemies = set(war_enemies(world, faction_id))
    return [
        other_id
        for other_id, other in sorted(world.factions.items())
        if other_id != faction_id
        and not other.is_destroyed
        and other.leader_id is not None
        and (include_player or not other.is_player)
        and other_id not in enemies
    ]


def _usable_grounds(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    target_id: FactionId,
) -> list[GroundState]:
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if leader is None:
        return []
    return sorted(
        (
            ground
            for ground in world.grounds
            if ground.holder_faction_id == faction_id
            and ground.target_faction_id == target_id
            and is_usable(world, scenario, ground)
        ),
        key=lambda ground: (
            -current_strength(ground, leader, scenario, world.clock.turn),
            ground.id,
        ),
    )


def _ratio_points(ratio: int, divisor: int) -> int:
    return _clamp((ratio - FULL_PERCENT) // divisor, -RATIO_SWING_CAP, RATIO_SWING_CAP)


def war_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    front_cost = tuning.second_front_penalty * len(war_enemies(world, faction_id))
    candidates: list[Candidate] = []
    for target_id in _eligible_targets(world, faction_id, include_player=True):
        grounds = _usable_grounds(world, scenario, faction_id, target_id)
        if leader is None or not grounds or is_bound(world, faction_id, target_id):
            continue
        strength = current_strength(grounds[0], leader, scenario, world.clock.turn)
        ratio = known_power_ratio(world, scenario, faction_id, target_id)
        base = (
            tuning.war_base_bonus
            + min(strength // tuning.ground_strength_divisor, STRENGTH_POINTS_CAP)
            + _ratio_points(ratio, tuning.ratio_divisor)
            - front_cost
        )
        order = DeclareWarOrder(
            faction_id=faction_id, target_faction_id=target_id, ground_id=grounds[0].id
        )
        candidates.append(Candidate(order, ScoreCategory.ATTACK, base))
    return candidates


def _has_open_play(
    world: WorldState, faction_id: FactionId, target_id: FactionId
) -> bool:
    return any(
        play.attacker_id == faction_id
        and play.defender_id == target_id
        and play.stage != "resolved"
        for play in world.plays
    )


def _region_demands(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    target_id: FactionId,
) -> list[Candidate]:
    knowledge = build_knowledge(world, scenario, faction_id)
    tuning = scenario.tuning.ai
    candidates: list[Candidate] = []
    for ground in _usable_grounds(world, scenario, faction_id, target_id):
        if ground.kind != GroundKind.CLAIM or ground.region_id is None:
            continue
        if knowledge.owners.get(ground.region_id) != target_id:
            continue
        term = CedeRegionTerm(
            from_faction_id=target_id,
            to_faction_id=faction_id,
            region_id=ground.region_id,
        )
        order = DiplomaticPlayOrder(
            faction_id=faction_id, target_faction_id=target_id, demands=[term]
        )
        base = min(
            ground.strength // tuning.ground_strength_divisor, STRENGTH_POINTS_CAP
        )
        candidates.append(Candidate(order, ScoreCategory.ATTACK, base))
        break
    return candidates


def demand_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    candidates: list[Candidate] = []
    for target_id in _eligible_targets(world, faction_id, include_player=False):
        ratio = known_power_ratio(world, scenario, faction_id, target_id)
        if ratio < tuning.demand_min_ratio or is_bound(world, faction_id, target_id):
            continue
        if _has_open_play(world, faction_id, target_id):
            continue
        gold = PayGoldTerm(
            payer_id=target_id, payee_id=faction_id, amount=tuning.demand_gold
        )
        order = DiplomaticPlayOrder(
            faction_id=faction_id, target_faction_id=target_id, demands=[gold]
        )
        base = max(_ratio_points(ratio, tuning.ratio_divisor), 0)
        candidates.append(Candidate(order, ScoreCategory.HOARD, base))
        candidates.extend(_region_demands(world, scenario, faction_id, target_id))
    return candidates


def talks_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    return [
        Candidate(
            CallNegotiationOrder(faction_id=faction_id, target_faction_id=target_id),
            ScoreCategory.ALLY,
        )
        for target_id in _eligible_targets(world, faction_id, include_player=False)
        if not _has_open_play(world, faction_id, target_id)
    ]


def _own_border_neighbors(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    target_id: FactionId,
) -> list[RegionId]:
    knowledge = build_knowledge(world, scenario, faction_id)
    own = {
        region_id
        for region_id, region in world.regions.items()
        if region.owner_id == faction_id
    }
    return sorted(
        region_id
        for region_id, owner_id in knowledge.owners.items()
        if owner_id == target_id
        and own & knowledge.index.neighbors.get(region_id, frozenset())
    )


def forgery_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    aim = world.aims.get(faction_id)
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if aim is None or leader is None or aim.category != ScoreCategory.ATTACK:
        return []
    target_id = aim.target_faction_id
    cunning = axis_totals(leader, scenario)[TraitAxis.CUNNING]
    if target_id is None or cunning <= 0 or target_id in war_enemies(world, faction_id):
        return []
    if _usable_grounds(world, scenario, faction_id, target_id):
        return []
    claimed = {
        ground.region_id
        for ground in world.grounds
        if ground.holder_faction_id == faction_id and ground.kind == GroundKind.CLAIM
    }
    regions = [
        region_id
        for region_id in _own_border_neighbors(world, scenario, faction_id, target_id)
        if region_id not in claimed
    ]
    if not regions:
        return []
    order = FabricateClaimOrder(
        faction_id=faction_id, target_faction_id=target_id, region_id=regions[0]
    )
    base = scenario.tuning.ai.forgery_bonus + min(cunning, CUNNING_POINTS_CAP)
    return [Candidate(order, ScoreCategory.ATTACK, base)]
