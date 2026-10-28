from collections.abc import Sequence

from app.engine.summaries.projection import project_summary_fact
from app.models.world_events import EventLogEntry, PendingSummaryFact, SummaryRequest
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.summary import MAX_SUMMARY_EVENTS, MAX_SUMMARY_PACKAGE_CHARS


def evaluate_corrected(
    world: WorldState,
    scenario: StrategyScenario,
    events: Sequence[EventLogEntry],
    previous: WorldState | None,
) -> SummaryRequest | None:
    unseen = {
        event.seq: event for event in events if event.seq > world.summary_event_cursor
    }
    has_major = False
    for sequence, event in sorted(unseen.items()):
        fact = project_summary_fact(world, event, previous)
        world.summary_event_cursor = sequence
        if fact is None:
            continue
        world.summary_pending_facts.append(
            PendingSummaryFact(seq=sequence, fact=fact, significance=event.significance)
        )
        world.significance.points += event.significance
        has_major |= event.is_major
    if not world.summary_pending_facts:
        return None
    if (
        not has_major
        and world.significance.points < scenario.tuning.summary_significance_threshold
    ):
        return None
    trigger = "major_event" if has_major else "significance"
    requests = _requests(world, trigger)
    world.summary_requests.extend(requests)
    world.summary_pending_facts = []
    world.significance.points = 0
    world.significance.last_summary_turn = world.clock.turn
    return requests[0]


def _requests(world: WorldState, trigger: str) -> list[SummaryRequest]:
    groups: list[list[PendingSummaryFact]] = [[]]
    size = 0
    for item in world.summary_pending_facts:
        item_size = len(item.fact.model_dump_json())
        if groups[-1] and (
            len(groups[-1]) >= MAX_SUMMARY_EVENTS
            or size + item_size > MAX_SUMMARY_PACKAGE_CHARS - 1024
        ):
            groups.append([])
            size = 0
        groups[-1].append(item)
        size += item_size
    return [
        SummaryRequest(
            id=f"summary:{group[0].seq}:{group[-1].seq}",
            requested_turn=world.clock.turn,
            event_seqs=[item.seq for item in group],
            facts=[item.fact for item in group],
            trigger=trigger,
        )
        for group in groups
    ]
