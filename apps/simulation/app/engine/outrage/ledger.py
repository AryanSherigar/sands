from app.engine.diplomacy.events import diplomacy_event
from app.engine.outrage.levels import LADDER
from app.engine.outrage.status import MOBILIZING_LEVELS, outrage_of
from app.engine.pressure.counters import add_humiliation
from app.models.world_diplomacy import OutrageState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import OutrageLevel

OUTRAGE_RAISED = "outrage_raised"
OUTRAGE_FADED = "outrage_faded"
OUTRAGE_REVEALED = "outrage_cause_revealed"


def _rank(level: OutrageLevel) -> int:
    return LADDER.index(level)


def _is_active(world: WorldState, scenario: StrategyScenario) -> bool:
    return world.outrage_ruleset >= 1 and scenario.toggles.is_outrage_enabled


def _upsert(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    offender_id: FactionId,
    level: OutrageLevel,
) -> OutrageState:
    tuning = scenario.tuning.outrage
    state = outrage_of(world, faction_id)
    if state is None:
        state = OutrageState(faction_id=faction_id, level=level, expires_turn=0)
        world.outrage.append(state)
    if _rank(level) >= _rank(state.level):
        state.level = level
    state.target_faction_id = offender_id
    state.expires_turn = world.clock.turn + tuning.enraged_turns
    if level in MOBILIZING_LEVELS:
        until = world.clock.turn + tuning.mobilization_turns
        state.mobilized_until_turn = max(state.mobilized_until_turn, until)
    return state


def _is_revealed_to_player(
    world: WorldState, offender_id: FactionId, level: OutrageLevel
) -> bool:
    return world.factions[offender_id].is_player and level in MOBILIZING_LEVELS


def raise_outrage(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    faction_id: FactionId,
    offender_id: FactionId,
    level: OutrageLevel,
) -> list[EventLogEntry]:
    if not _is_active(world, scenario) or level == OutrageLevel.NONE:
        return []
    _upsert(world, scenario, faction_id, offender_id, level)
    add_humiliation(
        world,
        scenario,
        faction_id,
        _rank(level) * scenario.tuning.outrage.humiliation_per_level,
    )
    world.outrage.sort(key=lambda item: item.faction_id)
    events = [
        diplomacy_event(
            OUTRAGE_RAISED, [faction_id, offender_id], {"level": _rank(level)}
        )
    ]
    if _is_revealed_to_player(world, offender_id, level):
        events.append(
            diplomacy_event(OUTRAGE_REVEALED, [offender_id, faction_id], is_major=True)
        )
    return events


def _fade(
    world: WorldState, scenario: StrategyScenario, state: OutrageState
) -> list[EventLogEntry]:
    state.level = LADDER[max(0, _rank(state.level) - 1)]
    state.expires_turn = world.clock.turn + scenario.tuning.outrage.enraged_turns
    return [
        diplomacy_event(
            OUTRAGE_FADED, [state.faction_id], {"level": _rank(state.level)}
        )
    ]


def tick_outrage(world: WorldState, scenario: StrategyScenario) -> list[EventLogEntry]:
    if not _is_active(world, scenario):
        return []
    events: list[EventLogEntry] = []
    for state in sorted(world.outrage, key=lambda item: item.faction_id):
        is_due = (
            state.level != OutrageLevel.NONE and world.clock.turn >= state.expires_turn
        )
        if is_due:
            events.extend(_fade(world, scenario, state))
    world.outrage = [
        state
        for state in world.outrage
        if state.level != OutrageLevel.NONE
        or world.clock.turn < state.mobilized_until_turn
    ]
    return events
