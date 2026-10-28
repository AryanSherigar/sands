from collections.abc import Callable
from typing import NamedTuple

from app.engine.ending_rules.end_date import is_end_date_reached
from app.engine.ending_rules.grade import compute_grade
from app.engine.ending_rules.hegemony import is_hegemon
from app.engine.ending_rules.negotiated_end import is_negotiated_end
from app.engine.ending_rules.regime_fall import is_regime_fallen
from app.engine.negotiation import player_faction_id
from app.engine.vassals.registry import vassalage_of
from app.exceptions.command_exceptions import GameEndedError
from app.models.world_events import EndingState
from app.models.world_faction import FactionState
from app.models.world_internal import is_rebel_faction
from app.models.world_state import WorldState
from strategy_contracts.scenario import EndingKind, StrategyScenario

CAPITAL_LOST_ENDING_ID = "default_defeat_capital_lost"
REVOLUTION_ENDING_ID = "default_defeat_revolution"
CONQUEST_ENDING_ID = "default_victory_conquest"
REGIME_FALL_ENDING_ID = "default_defeat_regime_fall"
HEGEMONY_ENDING_ID = "default_victory_hegemony"
NEGOTIATED_ENDING_ID = "default_graded_negotiated_peace"
END_DATE_ENDING_ID = "default_graded_end_date"
VASSAL_ENDING_ID = "default_graded_vassal_state"
GRADED_MINIMUM_RULESET = 2
REVOLUTION_STABILITY_FLOOR = 5
REVOLUTION_STREAK_TURNS = 8


def next_collapse_streak(world: WorldState) -> int:
    player = world.factions[player_faction_id(world)]
    if player.stability > REVOLUTION_STABILITY_FLOOR:
        return 0
    return world.stability_collapse_turns + 1


def is_capital_lost(world: WorldState) -> bool:
    player_id = player_faction_id(world)
    capital_id = world.factions[player_id].capital_region_id
    if capital_id is None:
        return False
    return world.regions[capital_id].owner_id != player_id


def is_revolution(world: WorldState) -> bool:
    return world.stability_collapse_turns >= REVOLUTION_STREAK_TURNS


def is_conquest(world: WorldState) -> bool:
    player_id = player_faction_id(world)
    rivals = [
        faction
        for key, faction in world.factions.items()
        if key != player_id and not is_rebel_faction(key)
    ]
    if not rivals:
        return False
    living = [faction for faction in rivals if not faction.is_destroyed]
    return all(_is_capital_held_by(world, faction, player_id) for faction in living)


def _is_capital_held_by(
    world: WorldState, faction: FactionState, holder_id: str
) -> bool:
    if faction.capital_region_id is None:
        return False
    return world.regions[faction.capital_region_id].owner_id == holder_id


class _PlainRule(NamedTuple):
    ending_id: str
    kind: EndingKind
    minimum_ruleset: int
    is_met: Callable[[WorldState, StrategyScenario], bool]


def _is_regime_fall_met(world: WorldState, scenario: StrategyScenario) -> bool:
    toggles = scenario.tuning.endings.toggles
    return toggles.is_regime_fall_enabled and is_regime_fallen(world, scenario)


def _is_hegemony_met(world: WorldState, scenario: StrategyScenario) -> bool:
    toggles = scenario.tuning.endings.toggles
    return toggles.is_hegemony_enabled and is_hegemon(world, scenario)


PLAIN_RULES = (
    _PlainRule(
        CAPITAL_LOST_ENDING_ID, EndingKind.DEFEAT, 1, lambda w, _: is_capital_lost(w)
    ),
    _PlainRule(
        REVOLUTION_ENDING_ID, EndingKind.DEFEAT, 1, lambda w, _: is_revolution(w)
    ),
    _PlainRule(REGIME_FALL_ENDING_ID, EndingKind.DEFEAT, 2, _is_regime_fall_met),
    _PlainRule(CONQUEST_ENDING_ID, EndingKind.VICTORY, 1, lambda w, _: is_conquest(w)),
    _PlainRule(HEGEMONY_ENDING_ID, EndingKind.VICTORY, 2, _is_hegemony_met),
)


def _graded_ending_id(world: WorldState, scenario: StrategyScenario) -> str | None:
    toggles = scenario.tuning.endings.toggles
    if toggles.is_negotiated_end_enabled and is_negotiated_end(world, scenario):
        return NEGOTIATED_ENDING_ID
    if not toggles.is_end_date_enabled or not is_end_date_reached(world, scenario):
        return None
    is_vassal = vassalage_of(world, player_faction_id(world)) is not None
    if is_vassal and toggles.is_vassal_outcome_enabled:
        return VASSAL_ENDING_ID
    return END_DATE_ENDING_ID


def _graded_ending(
    ending_id: str, world: WorldState, scenario: StrategyScenario
) -> EndingState:
    reading = compute_grade(world, scenario)
    return EndingState(
        ending_id=ending_id,
        kind=EndingKind.GRADED,
        turn=world.clock.turn,
        grade=reading.grade,
        inputs={**reading.inputs, "score": reading.score},
    )


def evaluate_default_endings(
    world: WorldState, scenario: StrategyScenario
) -> EndingState | None:
    for rule in PLAIN_RULES:
        if world.endings_ruleset >= rule.minimum_ruleset and rule.is_met(
            world, scenario
        ):
            return EndingState(
                ending_id=rule.ending_id, kind=rule.kind, turn=world.clock.turn
            )
    if world.endings_ruleset < GRADED_MINIMUM_RULESET:
        return None
    graded_id = _graded_ending_id(world, scenario)
    if graded_id is None:
        return None
    return _graded_ending(graded_id, world, scenario)


def require_game_not_ended(world: WorldState) -> None:
    if world.ending is not None:
        raise GameEndedError()
