from app.engine.diplomacy.events import diplomacy_event
from app.engine.endings import is_revolution
from app.engine.vassals.cleanup import clear_vassalage_state
from app.engine.vassals.registry import is_vassalage_in_force, vassal_term
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

VASSAL_FREED_BY_COLLAPSE = "vassal_freed_by_collapse"


def _has_lost_capital(world: WorldState, faction_id: FactionId) -> bool:
    capital_id = world.factions[faction_id].capital_region_id
    region = world.regions.get(capital_id) if capital_id is not None else None
    if region is None:
        return False
    return region.owner_id != faction_id or region.occupation is not None


def _has_collapsed(world: WorldState, faction_id: FactionId) -> bool:
    faction = world.factions[faction_id]
    if faction.is_destroyed or _has_lost_capital(world, faction_id):
        return True
    return faction.is_player and is_revolution(world)


def free_vassals_of_collapsed_overlords(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for commitment in sorted(world.commitments, key=lambda item: item.id):
        if not is_vassalage_in_force(world, commitment):
            continue
        term = vassal_term(commitment)
        if not _has_collapsed(world, term.overlord_id):
            continue
        commitment.status = CommitmentStatus.EXPIRED
        clear_vassalage_state(world, commitment.id)
        events.append(
            diplomacy_event(
                VASSAL_FREED_BY_COLLAPSE,
                [term.overlord_id, term.vassal_id],
                phase=PhaseName.TIME,
            )
        )
    return events
