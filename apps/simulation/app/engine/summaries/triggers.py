from collections.abc import Sequence

from app.engine.summaries.corrected import evaluate_corrected
from app.models.world_events import EventLogEntry, SummaryRequest
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def evaluate_summary_triggers(
    world: WorldState,
    scenario: StrategyScenario,
    events: Sequence[EventLogEntry],
    previous: WorldState | None = None,
) -> SummaryRequest | None:
    """Consume new events once and coalesce one player-safe chronicle request."""
    if world.summary_ruleset == 2:
        return evaluate_corrected(world, scenario, events, previous)
    if not world.summary_ruleset:
        return None
    unseen = [event for event in events if event.seq > world.summary_event_cursor]
    if not unseen:
        return None
    world.summary_event_cursor = max(event.seq for event in unseen)
    visible = [event for event in unseen if _is_player_known(world, event)]
    world.significance.points += sum(event.significance for event in visible)
    has_major = any(event.is_major for event in visible)
    threshold = (
        world.significance.points >= scenario.tuning.summary_significance_threshold
    )
    if not visible or not (has_major or threshold):
        return None
    trigger = "major_event" if has_major else "significance"
    request = SummaryRequest(
        id=f"summary:{visible[0].seq}:{visible[-1].seq}",
        requested_turn=world.clock.turn,
        event_seqs=[event.seq for event in visible],
        trigger=trigger,
    )
    world.summary_requests.append(request)
    world.significance.points = 0
    world.significance.last_summary_turn = world.clock.turn
    return request


def _is_player_known(world: WorldState, event: EventLogEntry) -> bool:
    player_id = next(
        (faction.id for faction in world.factions.values() if faction.is_player), None
    )
    if player_id is None or not event.cause.subject_ids:
        return False
    if player_id in event.cause.subject_ids:
        return True
    visible = _visible_subject_ids(world, player_id)
    return set(event.cause.subject_ids) <= visible


def _visible_subject_ids(world: WorldState, faction_id: str) -> set[str]:
    armies = {
        army_id for army_id, army in world.armies.items() if army.owner_id == faction_id
    }
    regions = {
        region_id
        for region_id, region in world.regions.items()
        if region.owner_id == faction_id
        or region_id in world.factions[faction_id].intel
    }
    return {faction_id, *armies, *regions}
