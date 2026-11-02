from app.engine.negotiation import player_faction_id
from app.engine.opinion import opinion_of
from app.engine.overtures.cards import demand_card, oath_term
from app.engine.overtures.ransom import (
    has_ransomable_captives,
    is_ransom_active,
)
from app.engine.overtures.renewals import pending_renewals
from app.engine.pressure.wars import find_war, side_score
from app.engine.pressure.weariness import is_war_weary
from app.engine.promises.signing import is_promise_in_force
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scenario import StrategyScenario


def is_overture_active(world: WorldState, scenario: StrategyScenario) -> bool:
    return world.overture_ruleset >= 1 and scenario.toggles.is_overtures_enabled


def _is_approachable(world: WorldState, faction_id: FactionId) -> bool:
    faction = world.factions[faction_id]
    if faction.is_player or faction.is_destroyed:
        return False
    if faction.leader_id is None or faction.leader_id not in world.leaders:
        return False
    return world.overture_cooldowns.get(faction_id, 0) <= world.clock.turn


def _kind_for(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    war: WarState,
) -> OvertureKind | None:
    tuning = scenario.tuning.overtures
    if is_war_weary(world, scenario, faction_id):
        return OvertureKind.PEACE_OFFER
    player_id = player_faction_id(world)
    edge = side_score(war, faction_id) - side_score(war, player_id)
    if edge >= tuning.demand_min_score_edge:
        has_demand = demand_card(world, scenario, faction_id) is not None
        return OvertureKind.DEMAND if has_demand else None
    if world.clock.turn - war.started_turn >= tuning.talks_min_war_turns:
        return OvertureKind.CALL_FOR_TALKS
    return None


def _ransom_holder(world: WorldState, scenario: StrategyScenario) -> FactionId | None:
    if not is_ransom_active(world):
        return None
    holders = sorted({item.held_by_id for item in world.prisoners})
    return next(
        (
            faction_id
            for faction_id in holders
            if _is_approachable(world, faction_id)
            and world.peace.ransom_demand_turns.get(faction_id, 0) <= world.clock.turn
            and has_ransomable_captives(world, scenario, faction_id)
        ),
        None,
    )


def _wants_to_swear(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    player_id = player_faction_id(world)
    if find_war(world, faction_id, player_id) is not None:
        return False
    leader = world.leaders[world.factions[faction_id].leader_id or ""]
    player_leader_id = world.factions[player_id].leader_id
    opinion = opinion_of(leader, player_leader_id)
    if opinion < scenario.tuning.overtures.oath_offer_min_opinion:
        return False
    return not is_promise_in_force(world, oath_term(world, scenario, faction_id))


def _oath_offerer(world: WorldState, scenario: StrategyScenario) -> FactionId | None:
    return next(
        (
            faction_id
            for faction_id in sorted(world.factions)
            if _is_approachable(world, faction_id)
            and _wants_to_swear(world, scenario, faction_id)
        ),
        None,
    )


def select_overture(
    world: WorldState, scenario: StrategyScenario
) -> tuple[FactionId, OvertureKind] | None:
    if not is_overture_active(world, scenario):
        return None
    renewals = pending_renewals(world)
    if renewals:
        return renewals[0][1], OvertureKind.HEIR_RENEWAL
    if is_ransom_active(world) and world.peace.ransom_counters:
        return world.peace.ransom_counters[0].origin_id, OvertureKind.RANSOM_COUNTER
    ransom_holder = _ransom_holder(world, scenario)
    if ransom_holder is not None:
        return ransom_holder, OvertureKind.RANSOM_DEMAND
    player_id = player_faction_id(world)
    for faction_id in sorted(world.factions):
        war = find_war(world, faction_id, player_id)
        if war is None or not _is_approachable(world, faction_id):
            continue
        kind = _kind_for(world, scenario, faction_id, war)
        if kind is not None:
            return faction_id, kind
    oath_offerer = _oath_offerer(world, scenario)
    if oath_offerer is not None:
        return oath_offerer, OvertureKind.OATH_OFFER
    return None
