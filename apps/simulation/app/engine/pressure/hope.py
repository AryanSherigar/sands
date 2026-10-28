from collections.abc import Callable

from app.engine.alliances.registry import allies_of
from app.engine.pressure.wars import side_of
from app.engine.vassals.registry import vassalage_partners
from app.models.world_battle import BattleStatus
from app.models.world_diplomacy import WarState
from app.models.world_pressure import HopeReading
from app.models.world_state import WorldState
from strategy_contracts.enums import ImprovementKind
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import HopeSource, ShockKind
from strategy_contracts.scenario import StrategyScenario

SourceFinder = Callable[[WorldState, StrategyScenario, FactionId, WarState], list[str]]


def _allied_army(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> list[str]:
    minimum = scenario.tuning.pressure.relief_army_min_morale
    busy = _busy_army_ids(world)
    side = side_of(war, faction_id)
    allies = {
        ally_id
        for ally_id in {
            *allies_of(world, faction_id),
            *vassalage_partners(world, faction_id),
        }
        if side is not None and side_of(war, ally_id) is side
    }
    return [
        f"allied_army:{army_id}"
        for army_id, army in sorted(world.armies.items())
        if army.owner_id in allies
        and army.morale >= minimum
        and sum(army.troops.values())
        and army_id not in busy
    ]


def _subsidy(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> list[str]:
    return [
        f"subsidy:{item.id}"
        for item in world.pressure.subsidies
        if item.receiver_id == faction_id
        and item.war_id == war.id
        and item.expires_turn >= world.clock.turn
    ]


def _mediation(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> list[str]:
    return [
        f"mediation:{item.id}"
        for item in world.pressure.mediation_offers
        if item.war_id == war.id and item.expires_turn >= world.clock.turn
    ]


def _busy_army_ids(world: WorldState) -> set[str]:
    return {
        army_id
        for battle in world.battles
        if battle.status != BattleStatus.RESOLVED
        for army_id in battle.attacker_army_ids + battle.defender_army_ids
    }


def _relief_army(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> list[str]:
    minimum = scenario.tuning.pressure.relief_army_min_morale
    busy = _busy_army_ids(world)
    return [
        f"relief_army:{army_id}"
        for army_id, army in sorted(world.armies.items())
        if army.owner_id == faction_id
        and army.morale >= minimum
        and sum(army.troops.values())
        and army_id not in busy
    ]


def _held_fortress(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> list[str]:
    return [
        f"held_fortress:{region_id}"
        for region_id, region in sorted(world.regions.items())
        if region.owner_id == faction_id
        and region.occupation is None
        and any(
            item.kind is ImprovementKind.FORT and item.turns_remaining == 0
            for item in region.improvements
        )
    ]


SOURCES: tuple[tuple[HopeSource, SourceFinder], ...] = (
    (HopeSource.ALLIED_ARMY, _allied_army),
    (HopeSource.SUBSIDY, _subsidy),
    (HopeSource.MEDIATION, _mediation),
    (HopeSource.RELIEF_ARMY, _relief_army),
    (HopeSource.HELD_FORTRESS, _held_fortress),
)


def _is_cancelled(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, war: WarState
) -> bool:
    window = scenario.tuning.pressure.hope_cancel_turns
    return any(
        shock.kind is ShockKind.NEW_ENEMY
        and shock.faction_id == faction_id
        and shock.war_id == war.id
        and shock.turn >= world.clock.turn - window
        for shock in world.pressure.shocks
    )


def derive_hope(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    war: WarState,
) -> HopeReading:
    if _is_cancelled(world, scenario, faction_id, war):
        return HopeReading(reasons=["cancelled:new_enemy"])
    reading = HopeReading()
    for source, find in SOURCES:
        reasons = find(world, scenario, faction_id, war)
        if reasons:
            reading.sources.append(source)
            reading.reasons += reasons
    if reading.sources:
        reading.bonus = scenario.tuning.pressure.hope_will_bonus
    return reading
