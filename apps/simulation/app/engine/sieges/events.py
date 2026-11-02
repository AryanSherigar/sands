from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from strategy_contracts.ids import ArmyId, FactionId, RegionId

SIGNIFICANCE_CONQUEST = 10
REGION_OCCUPIED = "region_occupied"


def siege_started(
    faction_id: FactionId, region_id: RegionId, army_ids: list[ArmyId]
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.SIEGES,
        kind="siege_started",
        cause=EventCause(
            summary_key="siege.started",
            subject_ids=[faction_id, region_id, *army_ids],
            inputs={"armies": len(army_ids)},
        ),
        changes=[
            StateChange(path=f"sieges.{region_id}", before=None, after=faction_id)
        ],
    )


def _siege_event(
    kind: str,
    summary_key: str,
    subject_ids: list[str],
    inputs: dict[str, int],
    changes: list[StateChange],
    significance: int = 0,
    phase: PhaseName = PhaseName.SIEGES,
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=phase,
        kind=kind,
        is_major=significance > 0,
        significance=significance,
        cause=EventCause(
            summary_key=summary_key, subject_ids=subject_ids, inputs=inputs
        ),
        changes=changes,
    )


def siege_progressed(
    faction_id: FactionId, region_id: RegionId, before: int, after: int
) -> EventLogEntry:
    return _siege_event(
        "siege_progressed",
        "siege.progressed",
        [faction_id, region_id],
        {"progress": after},
        [StateChange(path=f"sieges.{region_id}.progress", before=before, after=after)],
    )


def region_occupied(faction_id: FactionId, region_id: RegionId) -> EventLogEntry:
    return _siege_event(
        REGION_OCCUPIED,
        "siege.occupied",
        [faction_id, region_id],
        {},
        [
            StateChange(
                path=f"regions.{region_id}.occupation", before=None, after=faction_id
            )
        ],
    )


def region_conquered(
    faction_id: FactionId, previous_owner_id: FactionId, region_id: RegionId
) -> EventLogEntry:
    return _siege_event(
        "region_conquered",
        "siege.conquered",
        [faction_id, previous_owner_id, region_id],
        {},
        [
            StateChange(
                path=f"regions.{region_id}.owner_id",
                before=previous_owner_id,
                after=faction_id,
            )
        ],
        significance=SIGNIFICANCE_CONQUEST,
    )


def occupation_lifted(
    occupier_id: FactionId,
    owner_id: FactionId | None,
    region_id: RegionId,
    phase: PhaseName = PhaseName.SIEGES,
) -> EventLogEntry:
    subjects = (
        [occupier_id, region_id]
        if owner_id is None
        else [occupier_id, owner_id, region_id]
    )
    return _siege_event(
        "occupation_lifted",
        "siege.lifted",
        subjects,
        {},
        [
            StateChange(
                path=f"regions.{region_id}.occupation", before=occupier_id, after=None
            )
        ],
        phase=phase,
    )
