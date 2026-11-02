from uuid import UUID

from app.engine.event_numbering import number_events
from app.engine.judgments.effects import apply_judgment
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_events import EventLogEntry, PendingJudgment
from app.models.world_state import WorldState
from strategy_contracts.judgment import JudgmentOutcome
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome

HTTP_UNPROCESSABLE = 422
HTTP_NOT_FOUND = 404


def _require_valid_close(
    world: WorldState, scene_id: UUID, outcome: SceneOutcome
) -> tuple[PendingJudgment, JudgmentOutcome]:
    pending = world.progress.pending_judgment
    if world.progress.pending_scene_id != scene_id or pending is None:
        raise CampaignProgressError("scene unavailable", "not_found", HTTP_NOT_FOUND)
    if not isinstance(outcome, JudgmentOutcome):
        raise CampaignProgressError(
            "a judgment ends in one of its offered verdicts",
            "invalid_outcome",
            HTTP_UNPROCESSABLE,
        )
    return pending, outcome


def close_judgment(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    pending, judgment = _require_valid_close(world, scene_id, outcome)
    closed = world.model_copy(deep=True)
    events = apply_judgment(closed, scenario, pending, judgment)
    closed.progress.pending_scene_id = None
    closed.progress.pending_judgment = None
    closed.progress.negotiation_counterpart_id = None
    return closed, number_events(closed, events)
