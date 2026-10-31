from app.engine.ai.headless import run_headless
from app.engine.endings import NEGOTIATED_ENDING_ID
from app.engine.hashing import world_hash
from app.engine.peace.signing import sign_peace
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.engine.story_check import StoryCheckPhase
from app.models.world_events import PhaseName
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scenario import EndingKind

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_score,
)
from tests.engine.peace.builders import SCENARIO as FIXTURE_SCENARIO

RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
TURNS = 12
SEEDS = (3, 11)


def _scenario_ending_after_first_year():
    scenario = load_three_crowns_expanded()
    scenario.tuning.end_year = scenario.tuning.start_year
    return scenario


def test_headless_games_reach_the_same_graded_ending_on_replay() -> None:
    scenario = _scenario_ending_after_first_year()
    for seed in SEEDS:
        first = run_headless(scenario, seed, TURNS, RULER)
        second = run_headless(scenario, seed, TURNS, RULER)

        assert first.final_hash == second.final_hash
        assert first.final_world.ending == second.final_world.ending
        assert first.final_world.endings == second.final_world.endings


def test_a_game_past_the_end_date_has_a_graded_or_decisive_ending() -> None:
    scenario = _scenario_ending_after_first_year()
    world = run_headless(scenario, SEEDS[0], TURNS, RULER).final_world

    assert world is not None
    assert world.ending is not None
    if world.ending.kind is EndingKind.GRADED:
        assert world.ending.grade is not None


def test_ending_state_survives_a_document_round_trip() -> None:
    scenario = _scenario_ending_after_first_year()
    world = run_headless(scenario, SEEDS[1], TURNS, RULER).final_world
    assert world is not None

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.ending == world.ending


def _negotiated_peace_game() -> WorldState:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    context = PhaseContext(
        scenario=FIXTURE_SCENARIO,
        orders=(),
        rng=derive_rng(world.rng.seed, world.clock.turn, PhaseName.STORY_CHECK.value),
        resolved_outcomes={},
        recorded_answers={},
    )
    world = StoryCheckPhase().run(world, context).world
    card = make_peace_card(
        PLAYER, WRATHFUL_RIVAL, [], tier="generation", guarantor_ids=[CAUTIOUS_RIVAL]
    )
    sign_peace(world, FIXTURE_SCENARIO, card, "scene-1")
    world.clock.turn += 1
    return StoryCheckPhase().run(world, context).world


def test_a_war_ended_by_guaranteed_peace_ends_the_game_gradedly_and_replays() -> None:
    first = _negotiated_peace_game()
    second = _negotiated_peace_game()

    assert first.ending is not None
    assert first.ending.ending_id == NEGOTIATED_ENDING_ID
    assert first.ending.grade is not None
    assert world_hash(first) == world_hash(second)
