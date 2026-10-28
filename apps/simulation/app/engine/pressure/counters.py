from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario

MAX_DEVASTATION = 100


def update_stalemate(
    world: WorldState, scores_before: dict[str, tuple[int, int]]
) -> None:
    counters: dict[str, int] = {}
    for war in sorted(world.wars, key=lambda item: item.id):
        scores = (war.war_score_attacker, war.war_score_defender)
        previous = world.pressure.stalemate_turns.get(war.id)
        is_idle = previous is not None and scores_before.get(war.id) == scores
        counters[war.id] = previous + 1 if is_idle else 0
    world.pressure.stalemate_turns = counters


def add_humiliation(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    amount: int,
) -> None:
    current = world.pressure.humiliation.get(faction_id, 0)
    cap = scenario.tuning.pressure.humiliation_cap
    world.pressure.humiliation[faction_id] = min(cap, current + amount)


def raise_devastation(
    world: WorldState, scenario: StrategyScenario, region_id: RegionId
) -> None:
    step = scenario.tuning.pressure.devastation_step
    current = world.pressure.devastation.get(region_id, 0)
    world.pressure.devastation[region_id] = min(MAX_DEVASTATION, current + step)
