from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from app.models.world_internal import UprisingStage, UprisingState


def pressure_changed(
    faction_id: str,
    exhaustion_before: int,
    exhaustion_after: int,
    stability_before: int,
    stability_after: int,
    wars: int,
    losses: int,
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="faction_war_pressure_changed",
        cause=EventCause(
            summary_key="internal.war_pressure",
            subject_ids=[faction_id],
            inputs={"wars": wars, "battle_losses": losses},
        ),
        changes=[
            StateChange(
                path=f"factions.{faction_id}.war_exhaustion",
                before=exhaustion_before,
                after=exhaustion_after,
            ),
            StateChange(
                path=f"factions.{faction_id}.stability",
                before=stability_before,
                after=stability_after,
            ),
        ],
    )


def regional_unrest_changed(
    faction_id: str, region_id: str, before: int, after: int, pressure: int
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="regional_unrest_changed",
        cause=EventCause(
            summary_key="internal.regional_unrest",
            subject_ids=[faction_id, region_id],
            inputs={"pressure": pressure},
        ),
        changes=[
            StateChange(path=f"regions.{region_id}.unrest", before=before, after=after)
        ],
    )


def uprising_started(
    uprising_id: str, faction_id: str, region_id: str, unrest: int, chance: int
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="uprising_started",
        is_major=True,
        significance=10,
        cause=EventCause(
            summary_key="internal.uprising_started",
            subject_ids=[uprising_id, faction_id, region_id],
            inputs={"unrest": unrest, "chance_percent": chance},
        ),
    )


def uprising_resolved(
    uprising_id: str,
    faction_id: str,
    region_id: str,
    response: str,
    unrest_before: int,
    unrest_after: int,
    stability_before: int,
    stability_after: int,
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="uprising_resolved",
        is_major=True,
        significance=5,
        cause=EventCause(
            summary_key=f"internal.uprising_{response}",
            subject_ids=[uprising_id, faction_id, region_id],
        ),
        changes=[
            StateChange(
                path=f"regions.{region_id}.unrest",
                before=unrest_before,
                after=unrest_after,
            ),
            StateChange(
                path=f"factions.{faction_id}.stability",
                before=stability_before,
                after=stability_after,
            ),
        ],
    )


def uprising_stage_changed(
    uprising: UprisingState, before: UprisingStage
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="uprising_stage_changed",
        is_major=uprising.stage is UprisingStage.ARMED,
        significance=8,
        cause=EventCause(
            summary_key=f"internal.uprising_{uprising.archetype.value}_{uprising.stage.value}",
            subject_ids=[uprising.id, uprising.faction_id, uprising.region_id],
        ),
        changes=[
            StateChange(
                path=f"uprisings.{uprising.id}.stage",
                before=before.value,
                after=uprising.stage.value,
            )
        ],
    )


def uprising_flipped(
    uprising: UprisingState, previous_owner: str | None
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="uprising_flipped",
        is_major=True,
        significance=10,
        cause=EventCause(
            summary_key="internal.uprising_flipped",
            subject_ids=[uprising.id, uprising.faction_id, uprising.region_id],
        ),
        changes=[
            StateChange(
                path=f"regions.{uprising.region_id}.owner_id",
                before=previous_owner,
                after=None,
            )
        ],
    )


def rebel_army_raised(
    uprising: UprisingState, army_id: str, troops: int
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="rebel_army_raised",
        is_major=True,
        significance=10,
        cause=EventCause(
            summary_key="internal.rebel_army_raised",
            subject_ids=[uprising.id, uprising.faction_id, uprising.region_id],
            inputs={"troops": troops},
        ),
        changes=[
            StateChange(path=f"armies.{army_id}", before="absent", after="raised")
        ],
    )


def uprising_crushed(
    uprising: UprisingState, unrest_before: int, unrest_after: int
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind="uprising_crushed",
        is_major=True,
        significance=8,
        cause=EventCause(
            summary_key="internal.uprising_crushed",
            subject_ids=[uprising.id, uprising.faction_id, uprising.region_id],
        ),
        changes=[
            StateChange(
                path=f"regions.{uprising.region_id}.unrest",
                before=unrest_before,
                after=unrest_after,
            )
        ],
    )
