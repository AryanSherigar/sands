from dataclasses import dataclass, field

from app.engine.movement.map_index import MapIndex
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import MovementTuning


@dataclass
class MovementRun:
    world: WorldState
    index: MapIndex
    tuning: MovementTuning
    events: list[EventLogEntry] = field(default_factory=list)
