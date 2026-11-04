"""Loads the frozen scenario snapshot and narrative state for a turn (ADR-8)."""

import copy
import time
import uuid

import structlog
from app.exceptions.turn_exceptions import PlaythroughNotActiveError
from app.models.turn import LoadedState
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.turn_log_repo import TurnLogRepo

logger = structlog.get_logger()

EVENT_TURN_STEP_COMPLETED = "turn_step_completed"
STEP_NAME = "state_loader"
SNAPSHOT_VISIBILITY_KEY = "visibility"
PRIVATE_VISIBILITY = "private"


async def load_state(
    playthrough_id: uuid.UUID, playthrough_repo: PlaythroughRepo
) -> LoadedState:
    """Load scenario_snapshot and narrative state for the given playthrough.

    Reads only Playthrough.scenario_snapshot — never Scenario directly (ADR-8).
    """
    start = time.monotonic()
    playthrough = await playthrough_repo.get_by_id(playthrough_id)
    if playthrough is None:
        raise PlaythroughNotActiveError()

    logger.info(
        EVENT_TURN_STEP_COMPLETED,
        step_name=STEP_NAME,
        turn_count=playthrough.turn_count,
        duration_ms=(time.monotonic() - start) * 1000,
    )
    combat_events = 0
    if isinstance(playthrough.state.get("_combat"), dict):
        combat_events = await TurnLogRepo(playthrough_repo.session).count_combat_events(
            playthrough_id, playthrough.turn_count
        )
    return LoadedState(
        scenario_id=playthrough.scenario_id,
        scenario_snapshot=copy.deepcopy(playthrough.scenario_snapshot),
        state=copy.deepcopy(playthrough.state),
        turn_count=playthrough.turn_count,
        narrative_turn_count=playthrough.turn_count - combat_events,
        checkpoint=playthrough.checkpoint,
        is_playtest=playthrough.is_playtest,
        memory_publish_revision=playthrough.memory_publish_revision,
    )
