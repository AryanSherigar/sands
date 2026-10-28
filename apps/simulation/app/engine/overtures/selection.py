from app.engine.negotiation import player_faction_id
from app.engine.overtures.cards import demand_card
from app.engine.overtures.renewals import pending_renewals
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import find_war, side_score
from app.engine.pressure.will import compute_will
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


def _is_exhausted(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    tuning = scenario.tuning.overtures
    strain = compute_strain(world, scenario, faction_id).value
    will = compute_will(world, scenario, faction_id).value
    return (
        strain >= tuning.peace_offer_min_strain or will <= tuning.peace_offer_max_will
    )


def _kind_for(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    war: WarState,
) -> OvertureKind | None:
    tuning = scenario.tuning.overtures
    if _is_exhausted(world, scenario, faction_id):
        return OvertureKind.PEACE_OFFER
    player_id = player_faction_id(world)
    edge = side_score(war, faction_id) - side_score(war, player_id)
    if edge >= tuning.demand_min_score_edge:
        has_demand = demand_card(world, scenario, faction_id) is not None
        return OvertureKind.DEMAND if has_demand else None
    if world.clock.turn - war.started_turn >= tuning.talks_min_war_turns:
        return OvertureKind.CALL_FOR_TALKS
    return None


def select_overture(
    world: WorldState, scenario: StrategyScenario
) -> tuple[FactionId, OvertureKind] | None:
    if not is_overture_active(world, scenario):
        return None
    renewals = pending_renewals(world)
    if renewals:
        return renewals[0][1], OvertureKind.HEIR_RENEWAL
    player_id = player_faction_id(world)
    for faction_id in sorted(world.factions):
        war = find_war(world, faction_id, player_id)
        if war is None or not _is_approachable(world, faction_id):
            continue
        kind = _kind_for(world, scenario, faction_id, war)
        if kind is not None:
            return faction_id, kind
    return None
