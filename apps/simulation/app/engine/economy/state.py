from dataclasses import dataclass, field

from app.engine.movement.engagement import armies_in_open_battle
from app.models.world_events import EventLogEntry
from app.models.world_internal import is_rebel_faction
from app.models.world_state import WorldState
from strategy_contracts.ids import ArmyId, FactionId
from strategy_contracts.scenario import EconomyTuning, StrategyScenario


@dataclass
class EconomyRun:
    world: WorldState
    tuning: EconomyTuning
    is_loans_enabled: bool
    battle_army_ids: frozenset[ArmyId]
    can_pay_engaged: bool = False
    events: list[EventLogEntry] = field(default_factory=list)
    declared_defaults: set[FactionId] = field(default_factory=set)
    defaulted_factions: set[FactionId] = field(default_factory=set)
    fresh_loans: set[tuple[FactionId, int]] = field(default_factory=set)


def start_run(world: WorldState, scenario: StrategyScenario) -> EconomyRun:
    return EconomyRun(
        world=world,
        tuning=scenario.tuning.economy,
        is_loans_enabled=scenario.toggles.is_loans_enabled,
        battle_army_ids=frozenset(armies_in_open_battle(world)),
    )


def active_faction_ids(world: WorldState) -> list[FactionId]:
    return sorted(
        faction_id
        for faction_id, faction in world.factions.items()
        if not faction.is_destroyed and not is_rebel_faction(faction_id)
    )
