from app.engine.diplomacy.validation import is_at_war
from app.engine.diplomacy.war_score import winner_and_loser
from app.engine.sieges.events import siege_started
from app.engine.sieges.presence import armies_at, siege_at
from app.models.world_battle import BattleState
from app.models.world_events import EventLogEntry
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def start_sieges(world: WorldState, scenario: StrategyScenario) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for battle in sorted(world.battles, key=lambda item: item.id):
        events.extend(_start_after_battle(world, battle))
    return events


def _start_after_battle(world: WorldState, battle: BattleState) -> list[EventLogEntry]:
    result = winner_and_loser(battle)
    if result is None or battle.current_turn != world.clock.turn:
        return []
    winner, _ = result
    if not can_besiege(world, winner, battle.region_id):
        return []
    army_ids = armies_at(world, winner, battle.region_id)
    if not army_ids:
        return []
    world.sieges.append(
        SiegeState(region_id=battle.region_id, besieger_id=winner, army_ids=army_ids)
    )
    return [siege_started(winner, battle.region_id, army_ids)]


def can_besiege(world: WorldState, faction_id: str, region_id: str) -> bool:
    region = world.regions[region_id]
    owner = region.owner_id
    if owner is None or owner == faction_id or region.occupation is not None:
        return False
    if siege_at(world, region_id) or armies_at(world, owner, region_id):
        return False
    return is_at_war(world, faction_id, owner)
