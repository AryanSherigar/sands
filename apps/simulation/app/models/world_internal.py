from enum import Enum

from app.models.base import WorldModel
from strategy_contracts.ids import FactionId, Percent, RegionId, WholeNumber

REBEL_FACTION_ID = "rebels"


def is_rebel_faction(faction_id: str) -> bool:
    return faction_id == REBEL_FACTION_ID


class UprisingResponse(str, Enum):
    CONCESSIONS = "concessions"
    RESTORE_ORDER = "restore_order"
    NEGOTIATE = "negotiate"


class UprisingArchetype(str, Enum):
    PETITION = "petition"
    RIOT = "riot"
    REBELLION = "rebellion"


class UprisingStage(str, Enum):
    UNREST = "unrest"
    RIOT = "riot"
    ARMED = "armed"


STAGE_ORDER = (UprisingStage.UNREST, UprisingStage.RIOT, UprisingStage.ARMED)
STARTING_STAGE = {
    UprisingArchetype.PETITION: UprisingStage.UNREST,
    UprisingArchetype.RIOT: UprisingStage.RIOT,
    UprisingArchetype.REBELLION: UprisingStage.ARMED,
}
LEADERLESS_RESPONSES = frozenset({UprisingResponse.RESTORE_ORDER})


class UprisingState(WorldModel):
    id: str
    region_id: RegionId
    faction_id: FactionId
    started_turn: WholeNumber
    trigger_unrest: Percent
    income_penalty_percent: Percent
    manpower_penalty_percent: Percent
    supply_penalty_percent: Percent
    archetype: UprisingArchetype = UprisingArchetype.PETITION
    stage: UprisingStage = UprisingStage.UNREST
    turns_in_stage: WholeNumber = 0
    easing_turns: WholeNumber = 0
    has_rebel_army: bool = False


def uprising_for_region(
    uprisings: list[UprisingState], region_id: RegionId
) -> UprisingState | None:
    return next((item for item in uprisings if item.region_id == region_id), None)


def allowed_responses(uprising: UprisingState) -> frozenset[UprisingResponse]:
    if uprising.archetype is UprisingArchetype.RIOT:
        return LEADERLESS_RESPONSES
    return frozenset(UprisingResponse)
