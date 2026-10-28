from app.engine.diplomacy.reputation import shift_standing
from app.models.world_coalition import ConquestRecord
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario


def record_conquest(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    region_id: RegionId,
) -> None:
    if world.coalition_ruleset < 1:
        return
    world.coalition.conquests.append(
        ConquestRecord(
            turn=world.clock.turn,
            faction_id=faction_id,
            wealth=world.regions[region_id].wealth,
        )
    )
    shift_standing(
        world.factions[faction_id],
        -scenario.tuning.coalition.conquest_reputation_cost,
        0,
    )


def record_atrocity(world: WorldState, faction_id: FactionId) -> None:
    if world.coalition_ruleset < 1:
        return
    atrocities = world.coalition.atrocities
    atrocities[faction_id] = atrocities.get(faction_id, 0) + 1


def record_conquests(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    region_ids: list[RegionId],
) -> None:
    for region_id in region_ids:
        record_conquest(world, scenario, faction_id, region_id)
