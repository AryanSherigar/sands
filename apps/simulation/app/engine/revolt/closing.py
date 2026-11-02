from uuid import UUID

from app.engine.event_numbering import number_events
from app.engine.revolt.constants import HTTP_NOT_FOUND, HTTP_UNPROCESSABLE
from app.engine.revolt.effects import apply_revolt_option
from app.engine.revolt.options import is_option_available
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_events import EventLogEntry, PendingRevoltTalk
from app.models.world_state import WorldState
from strategy_contracts.revolt import OPTION_BY_ID, RevoltTalkOption
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ChoiceOutcome, SceneOutcome


def _require_valid_close(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[PendingRevoltTalk, RevoltTalkOption]:
    pending = world.progress.pending_revolt_talk
    if world.progress.pending_scene_id != scene_id or pending is None:
        raise CampaignProgressError("scene unavailable", "not_found", HTTP_NOT_FOUND)
    option = (
        OPTION_BY_ID.get(outcome.option_id)
        if isinstance(outcome, ChoiceOutcome)
        else None
    )
    if option is None or not is_option_available(world, scenario, pending, option):
        raise CampaignProgressError(
            "the people cannot be offered that",
            "invalid_outcome",
            HTTP_UNPROCESSABLE,
        )
    return pending, option


def close_revolt_talk(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    pending, option = _require_valid_close(world, scenario, scene_id, outcome)
    closed = world.model_copy(deep=True)
    events = apply_revolt_option(closed, scenario, pending, option, scene_id)
    closed.progress.pending_scene_id = None
    closed.progress.pending_revolt_talk = None
    closed.progress.negotiation_counterpart_id = None
    return closed, number_events(closed, events)
