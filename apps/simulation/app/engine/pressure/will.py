from app.engine.outrage.effects import mobilization_will
from app.engine.pressure.hope import derive_hope
from app.engine.pressure.shocks import shock_total
from app.engine.pressure.wars import side_score, wars_of
from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import WarState
from app.models.world_pressure import WillReading
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm
from strategy_contracts.traits import TraitAxis

FULL_PERCENT = 100
MORALE_WEIGHT = 40
UNITY_WEIGHT = 20
PLUNDER_WEIGHT = 10
INVASION_UNITY = 10
SUBSIDY_WILL = 5
TRAIT_FLOOR_STEP = 10
PEACE_PARTY_STABILITY = 40
STABILITY_PARTY_DIVISOR = 2
GOVERNOR_PARTY_DIVISOR = 5


def _enemy_ids(wars: list[WarState], faction_id: FactionId) -> set[str]:
    return {side for war in wars for side in (war.attacker_id, war.defender_id)} - {
        faction_id
    }


def _morale(world: WorldState, faction_id: FactionId) -> int:
    morales = [a.morale for a in world.armies.values() if a.owner_id == faction_id]
    average = sum(morales) // len(morales) if morales else 0
    return MORALE_WEIGHT * average // FULL_PERCENT


def _unity(world: WorldState, faction_id: FactionId) -> int:
    return UNITY_WEIGHT * world.factions[faction_id].stability // FULL_PERCENT


def _plunder(wars: list[WarState], faction_id: FactionId) -> int:
    best = max(side_score(war, faction_id) for war in wars)
    return PLUNDER_WEIGHT * best // FULL_PERCENT


def _invasion_unity(
    world: WorldState, wars: list[WarState], faction_id: FactionId
) -> int:
    enemies = _enemy_ids(wars, faction_id)
    is_invaded = any(
        army.owner_id in enemies
        and world.regions[army.location_id].owner_id == faction_id
        for army in world.armies.values()
    )
    return INVASION_UNITY if is_invaded else 0


def _subsidy(world: WorldState, wars: list[WarState], faction_id: FactionId) -> int:
    war_ids = {war.id for war in wars}
    is_funded = any(
        item.receiver_id == faction_id
        and item.war_id in war_ids
        and item.expires_turn >= world.clock.turn
        for item in world.pressure.subsidies
    )
    return SUBSIDY_WILL if is_funded else 0


def _independence(
    world: WorldState,
    scenario: StrategyScenario,
    wars: list[WarState],
    faction_id: FactionId,
) -> int:
    rebel_wars = [
        war
        for war in wars
        if war.id in world.vassal.independence_wars and war.attacker_id == faction_id
    ]
    return scenario.tuning.vassal.independence_will_bonus if rebel_wars else 0


def _party(world: WorldState, faction_id: FactionId) -> int:
    stability = world.factions[faction_id].stability
    shift = -max(0, PEACE_PARTY_STABILITY - stability) // STABILITY_PARTY_DIVISOR
    opinions = [
        governor.opinion_of_ruler
        for governor in world.governors.values()
        if world.regions[governor.region_id].owner_id == faction_id
    ]
    average = sum(opinions) // len(opinions) if opinions else 0
    return shift + min(0, average) // GOVERNOR_PARTY_DIVISOR


def _hope(
    world: WorldState,
    scenario: StrategyScenario,
    wars: list[WarState],
    faction_id: FactionId,
) -> int:
    return max(derive_hope(world, scenario, faction_id, war).bonus for war in wars)


def _trait_floor(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if leader is None:
        return 0
    totals = axis_totals(leader, scenario)
    spirit = totals[TraitAxis.PRIDE] + totals[TraitAxis.AGGRESSION]
    return max(0, (spirit - totals[TraitAxis.CAUTION]) * TRAIT_FLOOR_STEP)


def _extinction_floor(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    capital_id = world.factions[faction_id].capital_region_id
    is_extinction = any(
        play.stage != "resolved"
        and play.defender_id == faction_id
        and any(
            isinstance(term, CedeRegionTerm) and term.region_id == capital_id
            for term in play.demands
        )
        for play in world.plays
    )
    return scenario.tuning.pressure.extinction_floor if is_extinction else 0


def compute_will(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> WillReading:
    wars = wars_of(world, faction_id)
    if not wars or world.factions[faction_id].is_destroyed:
        return WillReading(value=0)
    shocks = shock_total(world, scenario, faction_id)
    factors = {
        "morale": _morale(world, faction_id),
        "unity": _unity(world, faction_id),
        "humiliation": scenario.tuning.pressure.humiliation_will_per_point
        * world.pressure.humiliation.get(faction_id, 0),
        "plunder": _plunder(wars, faction_id),
        "invasion_unity": _invasion_unity(world, wars, faction_id),
        "subsidy": _subsidy(world, wars, faction_id),
        "hope": _hope(world, scenario, wars, faction_id),
        "party": _party(world, faction_id),
        "shocks": -shocks,
    }
    independence = _independence(world, scenario, wars, faction_id)
    if independence:
        factors["independence"] = independence
    mobilization = mobilization_will(world, scenario, faction_id)
    if mobilization:
        factors["mobilization"] = mobilization
    floor = _trait_floor(world, scenario, faction_id)
    floor += _extinction_floor(world, scenario, faction_id) + factors["hope"]
    floor = min(FULL_PERCENT, max(0, floor - shocks))
    value = max(floor, min(FULL_PERCENT, sum(factors.values())))
    return WillReading(value=value, floor=floor, factors=factors)
