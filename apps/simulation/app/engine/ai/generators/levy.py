from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import war_enemies
from app.models.orders import RaiseArmyOrder
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.enums import TroopType
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

MAX_LEVY_REGIONS = 1
LEVY_MANPOWER_DIVISOR = 2


def _levy_size(region: RegionState, max_levy: int) -> int:
    return min(region.manpower // LEVY_MANPOWER_DIVISOR, max_levy)


def levy_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    own_armies = sum(1 for army in world.armies.values() if army.owner_id == faction_id)
    if own_armies >= tuning.max_armies:
        return []
    if world.factions[faction_id].treasury < tuning.low_treasury:
        return []
    regions = sorted(
        (
            region
            for region in world.regions.values()
            if region.owner_id == faction_id
            and region.occupation is None
            and _levy_size(region, tuning.max_levy) >= tuning.min_levy
        ),
        key=lambda region: (-region.manpower, region.id),
    )[:MAX_LEVY_REGIONS]
    need = tuning.situation_bonus if war_enemies(world, faction_id) else 0
    return [
        Candidate(
            RaiseArmyOrder(
                faction_id=faction_id,
                region_id=region.id,
                troops={TroopType.INFANTRY: _levy_size(region, tuning.max_levy)},
            ),
            ScoreCategory.ATTACK,
            need - tuning.levy_friction,
        )
        for region in regions
    ]
