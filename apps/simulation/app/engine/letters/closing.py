from uuid import UUID

from app.engine.letters.constants import (
    ACK_WARNING_WEIGHT,
    LETTER_ACK_WARNING,
    LETTER_COOL_CAUSE,
    LETTER_COOL_VALUE,
    LETTER_COOLER,
    LETTER_OPINION_FADE_PER_TURN,
    LETTER_OPTION_IDS,
    LETTER_WARM_CAUSE,
    LETTER_WARM_VALUE,
    LETTER_WARMER,
    WARNING_ACKNOWLEDGED,
)
from app.engine.negotiation import player_faction_id
from app.engine.negotiation_memory import record_memory
from app.engine.opinion import shift_opinion
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ChoiceOutcome, SceneOutcome

HTTP_UNPROCESSABLE = 422
HTTP_NOT_FOUND = 404
OPINION_SHIFTS = {
    LETTER_WARMER: (LETTER_WARM_CAUSE, LETTER_WARM_VALUE),
    LETTER_COOLER: (LETTER_COOL_CAUSE, LETTER_COOL_VALUE),
}


def _require_valid_close(
    world: WorldState, scene_id: UUID, outcome: SceneOutcome
) -> ChoiceOutcome:
    if (
        world.progress.pending_scene_id != scene_id
        or world.progress.pending_letter is None
    ):
        raise CampaignProgressError("scene unavailable", "not_found", HTTP_NOT_FOUND)
    if (
        not isinstance(outcome, ChoiceOutcome)
        or outcome.option_id not in LETTER_OPTION_IDS
    ):
        raise CampaignProgressError(
            "a letter ends in one of its offered replies",
            "invalid_outcome",
            HTTP_UNPROCESSABLE,
        )
    return outcome


def _apply_option(world: WorldState, sender_id: FactionId, option_id: str) -> None:
    player_id = player_faction_id(world)
    if option_id in OPINION_SHIFTS:
        cause, value = OPINION_SHIFTS[option_id]
        shift_opinion(
            world, sender_id, player_id, cause, value, LETTER_OPINION_FADE_PER_TURN
        )
    if option_id == LETTER_ACK_WARNING:
        sender = world.leaders[world.factions[sender_id].leader_id]
        record_memory(
            sender,
            WARNING_ACKNOWLEDGED,
            ACK_WARNING_WEIGHT,
            world.factions[player_id].leader_id,
            world.clock.turn,
        )


def close_letter(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    choice = _require_valid_close(world, scene_id, outcome)
    closed = world.model_copy(deep=True)
    pending = closed.progress.pending_letter
    _apply_option(closed, pending.sender_faction_id, choice.option_id)
    closed.progress.pending_scene_id = None
    closed.progress.pending_letter = None
    closed.progress.negotiation_counterpart_id = None
    return closed, []
