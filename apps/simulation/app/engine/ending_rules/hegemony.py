from app.engine.negotiation import player_faction_id
from app.models.world_internal import is_rebel_faction
from app.models.world_state import WorldState
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario


def _owns_share(owned: int, total: int, percent: int) -> bool:
    return total > 0 and owned * FULL_SHARE_PERCENT >= percent * total


def _owned_region_count(world: WorldState) -> int:
    player_id = player_faction_id(world)
    return sum(1 for region in world.regions.values() if region.owner_id == player_id)


def owned_region_percent(world: WorldState) -> int:
    return _owned_region_count(world) * FULL_SHARE_PERCENT // max(1, len(world.regions))


def _region_dominance(world: WorldState, scenario: StrategyScenario) -> bool:
    percent = scenario.tuning.endings.hegemony_region_percent
    return _owns_share(_owned_region_count(world), len(world.regions), percent)


def _wealth_dominance(world: WorldState, scenario: StrategyScenario) -> bool:
    player_id = player_faction_id(world)
    wealth = {
        key: max(0, faction.treasury)
        for key, faction in world.factions.items()
        if not faction.is_destroyed and not is_rebel_faction(key)
    }
    percent = scenario.tuning.endings.hegemony_wealth_percent
    return _owns_share(wealth.get(player_id, 0), sum(wealth.values()), percent)


def is_hegemonic_position(world: WorldState, scenario: StrategyScenario) -> bool:
    return _region_dominance(world, scenario) or _wealth_dominance(world, scenario)


def is_hegemon(world: WorldState, scenario: StrategyScenario) -> bool:
    streak = scenario.tuning.endings.hegemony_streak_turns
    return world.endings.hegemony_turns >= streak
