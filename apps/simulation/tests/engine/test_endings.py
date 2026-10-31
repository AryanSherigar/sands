from app.engine.endings import (
    CAPITAL_LOST_ENDING_ID,
    CONQUEST_ENDING_ID,
    REVOLUTION_ENDING_ID,
    REVOLUTION_STABILITY_FLOOR,
    REVOLUTION_STREAK_TURNS,
    evaluate_default_endings,
    next_collapse_streak,
    require_game_not_ended,
)
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.engine.story_check import StoryCheckPhase
from app.exceptions.command_exceptions import GameEndedError
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import EndingKind, StrategyScenario

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    make_faction,
    make_region,
    make_world,
)

PLAYER_CAPITAL = "player_capital"
RIVAL_CAPITAL = "rival_capital"


def _world() -> WorldState:
    world = make_world(
        regions=[
            make_region(PLAYER_CAPITAL, PLAYER),
            make_region(RIVAL_CAPITAL, RIVAL),
        ],
        factions=[
            make_faction(PLAYER, is_player=True, capital_region_id=PLAYER_CAPITAL),
            make_faction(RIVAL, capital_region_id=RIVAL_CAPITAL),
        ],
    )
    world.endings_ruleset = 1
    return world


def _context(scenario: StrategyScenario | None = None) -> PhaseContext:
    return PhaseContext(
        scenario=scenario or StrategyScenario(),
        orders=(),
        rng=derive_rng(11, 0, PhaseName.STORY_CHECK.value),
        resolved_outcomes={},
        recorded_answers={},
    )


def test_no_ending_when_nothing_has_happened() -> None:
    assert evaluate_default_endings(_world(), StrategyScenario()) is None


def test_losing_the_capital_is_a_defeat() -> None:
    world = _world()
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL

    ending = evaluate_default_endings(world, StrategyScenario())

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (
        CAPITAL_LOST_ENDING_ID,
        EndingKind.DEFEAT,
    )


def test_player_without_a_capital_cannot_lose_it() -> None:
    world = _world()
    world.factions[PLAYER].capital_region_id = None
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL

    assert evaluate_default_endings(world, StrategyScenario()) is None


def test_stability_above_floor_resets_the_streak() -> None:
    world = _world()
    world.stability_collapse_turns = 4
    world.factions[PLAYER].stability = REVOLUTION_STABILITY_FLOOR + 1

    assert next_collapse_streak(world) == 0


def test_stability_at_floor_extends_the_streak() -> None:
    world = _world()
    world.stability_collapse_turns = 4
    world.factions[PLAYER].stability = REVOLUTION_STABILITY_FLOOR

    assert next_collapse_streak(world) == 5


def test_streak_one_short_of_the_limit_is_not_a_revolution() -> None:
    world = _world()
    world.stability_collapse_turns = REVOLUTION_STREAK_TURNS - 1

    assert evaluate_default_endings(world, StrategyScenario()) is None


def test_full_streak_is_a_revolution() -> None:
    world = _world()
    world.stability_collapse_turns = REVOLUTION_STREAK_TURNS

    ending = evaluate_default_endings(world, StrategyScenario())

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (
        REVOLUTION_ENDING_ID,
        EndingKind.DEFEAT,
    )


def test_holding_every_rival_capital_is_a_victory() -> None:
    world = _world()
    world.regions[RIVAL_CAPITAL].owner_id = PLAYER

    ending = evaluate_default_endings(world, StrategyScenario())

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (
        CONQUEST_ENDING_ID,
        EndingKind.VICTORY,
    )


def test_all_rivals_destroyed_is_a_victory() -> None:
    world = _world()
    world.factions[RIVAL].is_destroyed = True

    ending = evaluate_default_endings(world, StrategyScenario())

    assert ending is not None
    assert ending.kind is EndingKind.VICTORY


def test_player_alone_has_no_conquest() -> None:
    world = make_world(
        regions=[make_region(PLAYER_CAPITAL, PLAYER)],
        factions=[
            make_faction(PLAYER, is_player=True, capital_region_id=PLAYER_CAPITAL)
        ],
    )

    assert evaluate_default_endings(world, StrategyScenario()) is None


def test_defeat_wins_a_same_turn_tie_with_victory() -> None:
    world = _world()
    world.regions[RIVAL_CAPITAL].owner_id = PLAYER
    world.stability_collapse_turns = REVOLUTION_STREAK_TURNS

    ending = evaluate_default_endings(world, StrategyScenario())

    assert ending is not None
    assert ending.kind is EndingKind.DEFEAT


def test_story_check_sets_ending_and_logs_one_event() -> None:
    world = _world()
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL

    result = StoryCheckPhase().run(world, _context())

    assert result.world.ending is not None
    assert result.world.ending.ending_id == CAPITAL_LOST_ENDING_ID
    assert [event.kind for event in result.events] == ["ending_reached"]


def test_story_check_tracks_the_collapse_streak() -> None:
    world = _world()
    world.factions[PLAYER].stability = REVOLUTION_STABILITY_FLOOR

    result = StoryCheckPhase().run(world, _context())

    assert result.world.stability_collapse_turns == 1
    assert result.world.ending is None


def test_story_check_ends_after_a_full_streak() -> None:
    world = _world()
    world.factions[PLAYER].stability = 0
    world.stability_collapse_turns = REVOLUTION_STREAK_TURNS - 1

    result = StoryCheckPhase().run(world, _context())

    assert result.world.ending is not None
    assert result.world.ending.ending_id == REVOLUTION_ENDING_ID


def test_story_check_is_inert_for_legacy_worlds() -> None:
    world = _world()
    world.endings_ruleset = 0
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL

    result = StoryCheckPhase().run(world, _context())

    assert result.world.ending is None
    assert result.events == []


def test_story_check_skips_scenarios_with_custom_endings() -> None:
    world = _world()
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL
    scenario = StrategyScenario(is_using_default_endings=False)

    result = StoryCheckPhase().run(world, _context(scenario))

    assert result.world.ending is None


def test_story_check_does_not_overwrite_an_existing_ending() -> None:
    world = _world()
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL
    first = StoryCheckPhase().run(world, _context()).world
    first_ending = first.ending
    first.regions[RIVAL_CAPITAL].owner_id = PLAYER
    first.clock.turn += 1

    second = StoryCheckPhase().run(first, _context())

    assert second.world.ending == first_ending
    assert second.events == []


def test_require_game_not_ended_blocks_an_ended_world() -> None:
    world = _world()
    world.regions[PLAYER_CAPITAL].owner_id = RIVAL
    ended = StoryCheckPhase().run(world, _context()).world

    require_game_not_ended(_world())
    try:
        require_game_not_ended(ended)
    except GameEndedError as error:
        assert error.code == "game_ended"
    else:
        raise AssertionError("expected GameEndedError")
