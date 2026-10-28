from app.engine.movement.costs import LegCost
from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from strategy_contracts.ids import ArmyId, EntityId, RegionId

ORDER_REJECTED = "movement_order_rejected"
MARCH_STARTED = "army_march_started"
ARMY_MOVED = "army_moved"
ARMY_ARRIVED = "army_arrived"
ARMY_EN_ROUTE = "army_en_route"
ARMY_HALTED = "army_halted"
ARMY_TURNED_BACK = "army_turned_back"
ARMY_RETURNING = "army_returning"
ARMY_RETURNED = "army_returned"
CONTACT_BATTLE = "contact_battle"
ENEMY_REGION_ENTERED = "enemy_region_entered"
BORDER_CONFRONTATION = "border_confrontation"
ROAD_MEETING = "road_meeting"
ADJUSTMENT_PREFIX = "adjust_"


def _entry(kind: str, cause: EventCause, changes: list[StateChange]) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.MOVEMENT,
        kind=kind,
        cause=cause,
        changes=changes,
    )


def _cost_inputs(cost: LegCost) -> dict[str, int]:
    inputs = {"base_cost": cost.base, "total_cost": cost.total}
    for adjustment in cost.adjustments:
        inputs[f"{ADJUSTMENT_PREFIX}{adjustment.reason}"] = adjustment.percent
    return inputs


def _location_change(army_id: ArmyId, before: RegionId, after: RegionId) -> StateChange:
    return StateChange(path=f"armies.{army_id}.location_id", before=before, after=after)


def order_rejected(army_id: EntityId, reason: str) -> EventLogEntry:
    cause = EventCause(summary_key=f"{ORDER_REJECTED}_{reason}", subject_ids=[army_id])
    return _entry(ORDER_REJECTED, cause, [])


def march_started(army_id: ArmyId, stops: int) -> EventLogEntry:
    cause = EventCause(
        summary_key=MARCH_STARTED, subject_ids=[army_id], inputs={"stops": stops}
    )
    return _entry(MARCH_STARTED, cause, [])


def army_moved(
    kind: str, army_id: ArmyId, before: RegionId, after: RegionId, cost: LegCost
) -> EventLogEntry:
    cause = EventCause(
        summary_key=kind,
        subject_ids=[army_id, after],
        inputs=_cost_inputs(cost),
    )
    return _entry(kind, cause, [_location_change(army_id, before, after)])


def army_en_route(
    army_id: ArmyId, destination: RegionId, progress: int, cost: LegCost
) -> EventLogEntry:
    inputs = _cost_inputs(cost) | {"leg_progress": progress}
    cause = EventCause(
        summary_key=ARMY_EN_ROUTE, subject_ids=[army_id, destination], inputs=inputs
    )
    return _entry(ARMY_EN_ROUTE, cause, [])


def army_halted(army_id: ArmyId, progress: int) -> EventLogEntry:
    cause = EventCause(
        summary_key=ARMY_HALTED,
        subject_ids=[army_id],
        inputs={"leg_progress": progress},
    )
    return _entry(ARMY_HALTED, cause, [])


def contact(
    kind: str, army_id: ArmyId, region_id: RegionId, others: list[ArmyId]
) -> EventLogEntry:
    cause = EventCause(summary_key=kind, subject_ids=[army_id, region_id, *others])
    return _entry(kind, cause, [])


def army_turned_back(army_id: ArmyId, progress: int) -> EventLogEntry:
    return _progress_event(ARMY_TURNED_BACK, army_id, progress)


def army_returning(army_id: ArmyId, progress_left: int) -> EventLogEntry:
    return _progress_event(ARMY_RETURNING, army_id, progress_left)


def army_returned(army_id: ArmyId, region_id: RegionId) -> EventLogEntry:
    cause = EventCause(summary_key=ARMY_RETURNED, subject_ids=[army_id, region_id])
    return _entry(ARMY_RETURNED, cause, [])


def _progress_event(kind: str, army_id: ArmyId, progress: int) -> EventLogEntry:
    cause = EventCause(
        summary_key=kind, subject_ids=[army_id], inputs={"leg_progress": progress}
    )
    return _entry(kind, cause, [])
