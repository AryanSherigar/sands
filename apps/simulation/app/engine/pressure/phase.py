from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.bands import to_band
from app.engine.pressure.counters import raise_devastation
from app.engine.pressure.forcers import expire_mediation, expire_subsidies
from app.engine.pressure.rumors import file_rumors
from app.engine.pressure.shocks import detect_state_shocks
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.engine.rng import DeterministicRng
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _enemy_ids(world: WorldState, faction_id: FactionId) -> set[FactionId]:
    sides = {
        side
        for war in wars_of(world, faction_id)
        for side in (war.attacker_id, war.defender_id)
    }
    return sides - {faction_id}


def _is_ravaged(world: WorldState, region_id: str, enemy_ids: set[str]) -> bool:
    region = world.regions[region_id]
    if region.occupation is not None and region.occupation.occupier_id in enemy_ids:
        return True
    return any(
        army.owner_id in enemy_ids and army.location_id == region_id
        for army in world.armies.values()
    )


def _ravage_regions(world: WorldState, scenario: StrategyScenario) -> None:
    for region_id, region in sorted(world.regions.items()):
        if region.owner_id is None:
            continue
        enemy_ids = _enemy_ids(world, region.owner_id)
        if enemy_ids and _is_ravaged(world, region_id, enemy_ids):
            raise_devastation(world, scenario, region_id)


def _band_key(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> str:
    tuning = scenario.tuning.pressure
    will = to_band(compute_will(world, scenario, faction_id).value, tuning)
    strain = to_band(compute_strain(world, scenario, faction_id).value, tuning)
    return f"{will.value}:{strain.value}"


def _report_band_changes(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    current: dict[FactionId, str] = {}
    for faction_id, faction in sorted(world.factions.items()):
        if faction.is_destroyed or not wars_of(world, faction_id):
            continue
        current[faction_id] = _band_key(world, scenario, faction_id)
        previous = world.pressure.last_bands.get(faction_id)
        if previous is not None and previous != current[faction_id]:
            events.append(
                diplomacy_event(
                    "pressure_band_changed", [faction_id], phase=PhaseName.TIME
                )
            )
    world.pressure.last_bands = current
    return events


def tick_pressure(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    if not world.pressure_ruleset:
        return []
    _ravage_regions(world, scenario)
    detect_state_shocks(world, scenario)
    expire_mediation(world)
    expire_subsidies(world)
    events = _report_band_changes(world, scenario)
    return events + file_rumors(world, scenario, rng)
