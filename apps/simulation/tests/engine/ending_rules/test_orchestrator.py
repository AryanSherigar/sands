from app.engine.ending_rules.end_date import current_year
from app.engine.endings import (
    CAPITAL_LOST_ENDING_ID,
    CONQUEST_ENDING_ID,
    END_DATE_ENDING_ID,
    HEGEMONY_ENDING_ID,
    NEGOTIATED_ENDING_ID,
    REGIME_FALL_ENDING_ID,
    VASSAL_ENDING_ID,
    evaluate_default_endings,
)
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.engine.story_check import StoryCheckPhase
from app.models.world_events import PhaseName
from app.models.world_internal import is_rebel_faction
from app.models.world_state import WorldState
from strategy_contracts.endings import EndingGrade
from strategy_contracts.scenario import EndingKind, StrategyScenario

from tests.engine.ending_rules.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_truce,
    add_war,
    make_world,
    scenario_with,
)
from tests.engine.vassals.builders import add_vassalage

MONTHS_PER_YEAR = 12


def _context(scenario: StrategyScenario) -> PhaseContext:
    return PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(11, 0, PhaseName.STORY_CHECK.value),
        resolved_outcomes={},
        recorded_answers={},
    )


def _past_end_date(world: WorldState) -> WorldState:
    world.clock.start_year = SCENARIO.tuning.end_year + 1
    assert current_year(world) > SCENARIO.tuning.end_year
    return world


def _hegemon_world() -> WorldState:
    world = make_world()
    for region in world.regions.values():
        region.owner_id = PLAYER
    world.endings.hegemony_turns = SCENARIO.tuning.endings.hegemony_streak_turns
    return world


def test_fresh_world_has_no_ending() -> None:
    assert evaluate_default_endings(make_world(), SCENARIO) is None


def test_ruleset_1_ignores_new_endings() -> None:
    world = _past_end_date(_hegemon_world())
    world.endings_ruleset = 1
    for faction_id, faction in world.factions.items():
        if faction_id != PLAYER and not is_rebel_faction(faction_id):
            faction.is_destroyed = False

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is None or ending.ending_id == CONQUEST_ENDING_ID


def test_hegemony_is_a_victory() -> None:
    world = _hegemon_world()
    for faction_id, faction in world.factions.items():
        if faction_id != PLAYER:
            faction.capital_region_id = None

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert (ending.ending_id, ending.kind) in {
        (HEGEMONY_ENDING_ID, EndingKind.VICTORY),
        (CONQUEST_ENDING_ID, EndingKind.VICTORY),
    }


def test_regime_fall_is_a_defeat() -> None:
    world = make_world()
    world.endings.regime_fall_turns = SCENARIO.tuning.endings.regime_fall_streak_turns

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (REGIME_FALL_ENDING_ID, EndingKind.DEFEAT)


def test_precedence_capital_lost_beats_hegemony() -> None:
    world = _hegemon_world()
    capital = world.factions[PLAYER].capital_region_id
    assert capital is not None
    world.regions[capital].owner_id = CAUTIOUS_RIVAL

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert ending.ending_id == CAPITAL_LOST_ENDING_ID


def test_victory_beats_graded_same_turn() -> None:
    world = _past_end_date(_hegemon_world())

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert ending.kind is EndingKind.VICTORY


def test_disabled_toggle_skips_ending() -> None:
    world = make_world()
    world.endings.regime_fall_turns = SCENARIO.tuning.endings.regime_fall_streak_turns
    scenario = scenario_with(toggles={"is_regime_fall_enabled": False})

    assert evaluate_default_endings(world, scenario) is None


def test_end_date_graded_ending_has_grade() -> None:
    world = _past_end_date(make_world())

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (END_DATE_ENDING_ID, EndingKind.GRADED)
    assert ending.grade in set(EndingGrade)
    assert {"score", "position", "strain"} <= set(ending.inputs)


def test_vassal_at_end_date_gets_vassal_ending() -> None:
    world = _past_end_date(make_world())
    add_vassalage(world, CAUTIOUS_RIVAL, PLAYER)

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert ending.ending_id == VASSAL_ENDING_ID
    assert ending.grade in {EndingGrade.BITTER, EndingGrade.RUIN}


def test_negotiated_end_is_graded() -> None:
    world = make_world()
    add_war(world)
    world.endings.has_seen_war = True
    world.wars.clear()
    add_truce(world, expires_in=50, guarantor_ids=[CAUTIOUS_RIVAL])

    ending = evaluate_default_endings(world, SCENARIO)

    assert ending is not None
    assert (ending.ending_id, ending.kind) == (NEGOTIATED_ENDING_ID, EndingKind.GRADED)


def test_ending_event_carries_grade_inputs() -> None:
    world = _past_end_date(make_world())

    result = StoryCheckPhase().run(world, _context(SCENARIO))

    assert result.world.ending is not None
    assert [event.kind for event in result.events] == ["ending_reached"]
    assert "score" in result.events[0].cause.inputs


def test_story_check_advances_streaks_at_ruleset_2() -> None:
    world = _hegemon_world()
    world.endings.hegemony_turns = 0

    result = StoryCheckPhase().run(world, _context(SCENARIO))

    assert result.world.endings.hegemony_turns == 1
