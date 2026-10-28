from collections.abc import Callable
from uuid import UUID

from app.engine.negotiation import close_negotiation
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome, SceneType, TermsCardOutcome

SceneCloser = Callable[
    [WorldState, StrategyScenario, UUID, SceneOutcome],
    tuple[WorldState, list[EventLogEntry]],
]


def _close_negotiation_scene(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    if not isinstance(outcome, TermsCardOutcome):
        raise CampaignProgressError(
            "a negotiation ends in terms", "invalid_outcome", 422
        )
    return close_negotiation(
        world,
        scenario,
        scene_id,
        outcome.terms_card,
        outcome.result,
        outcome.refused_demand,
    )


SCENE_CLOSERS: dict[SceneType, SceneCloser] = {
    SceneType.NEGOTIATION: _close_negotiation_scene,
    SceneType.PEACE: _close_negotiation_scene,
}


def close_scene(
    world: WorldState,
    scenario: StrategyScenario,
    scene_type: SceneType,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    """Apply a scene's final outcome to the world; the one pure path live play and replay share."""
    closer = SCENE_CLOSERS.get(scene_type)
    if closer is None:
        raise CampaignProgressError("unsupported scene type", "invalid_lifecycle")
    return closer(world, scenario, scene_id, outcome)
