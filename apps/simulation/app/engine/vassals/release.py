from app.engine.diplomacy.events import diplomacy_event
from app.engine.vassals.cleanup import clear_vassalage_state
from app.engine.vassals.registry import vassal_term, vassalage_by_id
from app.exceptions.command_exceptions import CommandError
from app.models.orders import ReleaseVassalOrder
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState

VASSAL_RELEASED = "vassal_released"
HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def validate_release_vassal(world: WorldState, order: ReleaseVassalOrder) -> None:
    commitment = vassalage_by_id(world, order.vassalage_id)
    if commitment is None:
        raise _reject("unknown_vassalage")
    if vassal_term(commitment).overlord_id != order.faction_id:
        raise _reject("not_overlord")


def release_vassal(world: WorldState, order: ReleaseVassalOrder) -> list[EventLogEntry]:
    commitment = vassalage_by_id(world, order.vassalage_id)
    assert commitment is not None
    term = vassal_term(commitment)
    commitment.status = CommitmentStatus.EXPIRED
    clear_vassalage_state(world, commitment.id)
    return [diplomacy_event(VASSAL_RELEASED, [term.overlord_id, term.vassal_id])]
