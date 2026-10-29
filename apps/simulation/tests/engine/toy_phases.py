from collections.abc import Callable

from app.engine.economy.phase import EconomyPhase
from app.engine.ordering import sorted_items
from app.engine.phases import Phase, PhaseContext, PhaseResult
from app.engine.rng import DeterministicRng
from app.models.world_events import (
    PHASE_ORDER,
    EventCause,
    EventLogEntry,
    PendingEvent,
    PhaseName,
)
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.conditions import ConditionScope

PERCENT_MAX = 100
MORALE_SWING = 3
UNREST_MIN_STEP = -2
UNREST_MAX_STEP = 3
GARRISON_GROWTH = 3
REPUTATION_SWING = 2
MOVE_ONE_IN = 2
TOY_EVENT_TEMPLATE = "toy_event"

ToyStep = Callable[[WorldState, DeterministicRng, PhaseContext], None]


def _clamp(value: int, low: int = 0, high: int = PERCENT_MAX) -> int:
    return max(low, min(high, value))


def _diplomacy(world: WorldState, rng: DeterministicRng, _: PhaseContext) -> None:
    faction_ids = rng.shuffled(
        [faction_id for faction_id, _ in sorted_items(world.factions)]
    )
    faction = world.factions[faction_ids[0]]
    swing = rng.roll_range(-REPUTATION_SWING, REPUTATION_SWING)
    faction.reputation = _clamp(faction.reputation + swing, -PERCENT_MAX)


def _movement(world: WorldState, rng: DeterministicRng, context: PhaseContext) -> None:
    neighbors = {
        region.id: region.neighbor_ids for region in context.scenario.map.regions
    }
    for army_id, army in sorted_items(world.armies):
        army_rng = rng.fork(army_id)
        options = sorted(neighbors[army.location_id])
        if options and army_rng.roll(MOVE_ONE_IN) == 0:
            army.location_id = army_rng.shuffled(options)[0]


def _battles(world: WorldState, rng: DeterministicRng, _: PhaseContext) -> None:
    for army_id, army in sorted_items(world.armies):
        swing = rng.fork(army_id).roll_range(-MORALE_SWING, MORALE_SWING)
        army.morale = _clamp(army.morale + swing)


def _sieges(world: WorldState, rng: DeterministicRng, _: PhaseContext) -> None:
    for region_id, region in sorted_items(world.regions):
        region.garrison += rng.fork(region_id).roll(GARRISON_GROWTH)


def _internal(world: WorldState, rng: DeterministicRng, _: PhaseContext) -> None:
    for region_id, region in sorted_items(world.regions):
        step = rng.fork(region_id).roll_range(UNREST_MIN_STEP, UNREST_MAX_STEP)
        region.unrest = _clamp(region.unrest + step)


def _time(world: WorldState, rng: DeterministicRng, _: PhaseContext) -> None:
    for _faction_id, faction in sorted_items(world.factions):
        faction.war_exhaustion = _clamp(faction.war_exhaustion - 1)


def _events(world: WorldState, rng: DeterministicRng, context: PhaseContext) -> None:
    frequency = context.scenario.tuning.event_frequency_percent
    if rng.roll(PERCENT_MAX) >= frequency:
        return
    count = world.counters.get(CounterKind.PENDING_EVENT, 0) + 1
    world.counters[CounterKind.PENDING_EVENT] = count
    world.pending_events.append(
        PendingEvent(
            id=f"event_{count}",
            template_id=TOY_EVENT_TEMPLATE,
            choice_ids=["choice_a", "choice_b"],
            subject_kind=ConditionScope.FACTION,
            subject_id="toy_subject",
            subject_name="Toy subject",
            tier=1,
            created_turn=world.clock.turn,
            deadline_turn=world.clock.turn + 1,
            cause_key="toy_event",
        )
    )


def _nothing(world: WorldState, rng: DeterministicRng, context: PhaseContext) -> None:
    return None


TOY_STEPS: dict[PhaseName, ToyStep] = {
    PhaseName.ORDERS: _nothing,
    PhaseName.DIPLOMACY: _diplomacy,
    PhaseName.MOVEMENT: _movement,
    PhaseName.BATTLES: _battles,
    PhaseName.SIEGES: _sieges,
    PhaseName.INTERNAL: _internal,
    PhaseName.TIME: _time,
    PhaseName.EVENTS: _events,
    PhaseName.STORY_CHECK: _nothing,
}


class ToyPhase:
    def __init__(self, name: PhaseName, step: ToyStep | None = None) -> None:
        self.name = name
        self._step = step or TOY_STEPS[name]

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        self._step(world, context.rng, context)
        event = EventLogEntry(
            seq=0,
            turn=0,
            phase=self.name,
            kind="toy",
            cause=EventCause(summary_key=f"toy_{self.name.value}"),
        )
        return PhaseResult(world=world, events=[event])


def toy_phases(
    overrides: dict[PhaseName, Phase] | None = None,
) -> dict[PhaseName, Phase]:
    phases: dict[PhaseName, Phase] = {
        name: ToyPhase(name) for name in PHASE_ORDER if name is not PhaseName.ECONOMY
    }
    phases[PhaseName.ECONOMY] = EconomyPhase()
    return phases | (overrides or {})
