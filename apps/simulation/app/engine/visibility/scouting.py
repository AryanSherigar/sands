from app.engine.movement.knowledge import visible_regions
from app.engine.movement.map_index import MapIndex, build_map_index
from app.engine.rng import derive_rng
from app.exceptions.command_exceptions import CommandError
from app.models.world_region import RegionIntel
from app.models.world_state import WorldState
from app.models.world_visibility import MapScoutReport
from strategy_contracts.scenario import StrategyScenario

MAX_DECEPTIVE_COVERAGE = 99


def validate_map_scout_target(
    world: WorldState, faction_id: str, target_region_id: str, index: MapIndex
) -> None:
    visible = visible_regions(world, faction_id, index)
    is_adjacent = any(
        target_region_id in index.neighbors[region_id] for region_id in visible
    )
    if (
        faction_id not in world.factions
        or target_region_id not in world.regions
        or target_region_id in visible
        or not is_adjacent
    ):
        raise CommandError("map scout target unavailable", "invalid_scout_target", 422)


def resolve_map_scout(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    target_region_id: str,
    mission_id: str,
    *,
    is_deceived: bool = False,
) -> MapScoutReport:
    index = build_map_index(scenario.map)
    validate_map_scout_target(world, faction_id, target_region_id, index)
    coverage = _coverage(
        world, scenario, faction_id, target_region_id, mission_id, is_deceived
    )
    region = world.regions[target_region_id]
    has_full_coverage = coverage == 100
    return MapScoutReport(
        id=mission_id,
        observer_faction_id=faction_id,
        target_region_id=target_region_id,
        observed_turn=world.clock.turn,
        coverage_percent=coverage,
        owner_id=region.owner_id if coverage >= 50 else None,
        garrison_estimate=_estimate(region.garrison, world.clock.turn)
        if coverage >= 75
        else None,
        is_accurate=has_full_coverage,
    )


def _coverage(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    target_region_id: str,
    mission_id: str,
    is_deceived: bool,
) -> int:
    tuning = scenario.tuning.visibility
    rng = derive_rng(
        world.rng.seed,
        world.clock.turn,
        "map_scout",
        faction_id,
        target_region_id,
        mission_id,
    )
    coverage = rng.roll_range(
        tuning.map_scout_min_coverage, tuning.map_scout_max_coverage
    )
    return min(coverage, MAX_DECEPTIVE_COVERAGE) if is_deceived else coverage


def _estimate(garrison: int, turn: int) -> RegionIntel:
    return RegionIntel(
        last_seen_turn=turn,
        owner_id=None,
        garrison_low=max(0, garrison - 10),
        garrison_high=garrison + 10,
    )
