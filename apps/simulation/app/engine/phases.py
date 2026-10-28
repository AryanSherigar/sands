from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

from app.engine.rng import DeterministicRng
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.orders import QueuedOrder
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome, SceneType


@dataclass(frozen=True)
class ScenePause:
    scene_type: SceneType
    subject_ids: tuple[str, ...]


@dataclass(frozen=True)
class PhaseCheckpoint:
    waiting_reason: Literal["awaiting_commands", "awaiting_battle_decision"] = (
        "awaiting_commands"
    )


@dataclass(frozen=True)
class PhaseContext:
    scenario: StrategyScenario
    orders: tuple[QueuedOrder, ...]
    rng: DeterministicRng
    resolved_outcomes: Mapping[UUID, SceneOutcome]
    recorded_answers: Mapping[str, str]


@dataclass
class PhaseResult:
    world: WorldState
    events: list[EventLogEntry] = field(default_factory=list)
    pause: ScenePause | None = None
    checkpoint: PhaseCheckpoint | None = None

    def __post_init__(self) -> None:
        if self.pause is not None and self.checkpoint is not None:
            raise CampaignProgressError("phase cannot pause and checkpoint together")


class Phase(Protocol):
    """A phase gets a private deep copy of the world, may mutate and return it.

    On a pause the pipeline discards the phase's output and re-runs the same
    phase once the scene resolves; the service sets world.progress.pending_scene_id
    so the re-run finds its outcome in context.resolved_outcomes. A checkpoint instead
    accepts the returned world/events and retains the same phase cursor.
    """

    name: PhaseName

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult: ...
