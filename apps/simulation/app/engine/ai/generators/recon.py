from app.engine.ai.candidates import Candidate
from app.engine.ai.knowledge import Knowledge, build_knowledge
from app.models.orders import MapScoutOrder
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

MAX_SCOUTS = 2


def _is_stale(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    region_id: RegionId,
) -> bool:
    intel = world.factions[faction_id].intel.get(region_id)
    if intel is None:
        return True
    age = world.clock.turn - intel.last_seen_turn
    return age >= scenario.tuning.ai.scout_stale_turns


def _is_next_to_sight(knowledge: Knowledge, region_id: RegionId) -> bool:
    return any(
        region_id in knowledge.index.neighbors.get(seen, frozenset())
        for seen in knowledge.visible
    )


def _faces_target(
    world: WorldState, faction_id: FactionId, knowledge: Knowledge, region_id: RegionId
) -> bool:
    aim = world.aims.get(faction_id)
    if aim is None or aim.target_faction_id is None:
        return False
    return any(
        knowledge.owners.get(neighbor) == aim.target_faction_id
        for neighbor in knowledge.index.neighbors.get(region_id, frozenset())
    )


def scout_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    knowledge = build_knowledge(world, scenario, faction_id)
    unknown = [
        region_id
        for region_id in sorted(world.regions)
        if region_id not in knowledge.visible
        and _is_next_to_sight(knowledge, region_id)
        and _is_stale(world, scenario, faction_id, region_id)
    ]
    ranked = sorted(
        unknown,
        key=lambda region_id: (
            not _faces_target(world, faction_id, knowledge, region_id),
            region_id,
        ),
    )
    return [
        Candidate(
            MapScoutOrder(faction_id=faction_id, target_region_id=region_id),
            ScoreCategory.EXPAND,
        )
        for region_id in ranked[:MAX_SCOUTS]
    ]
