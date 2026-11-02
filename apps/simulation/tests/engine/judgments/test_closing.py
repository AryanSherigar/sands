import pytest
from app.engine.hashing import world_hash
from app.engine.judgments.closing import close_judgment
from app.engine.scene_closing import close_scene
from app.exceptions.command_exceptions import CampaignProgressError
from strategy_contracts.judgment import JudgmentNuance, JudgmentOutcome, JudgmentVerdict
from strategy_contracts.scene import ChoiceOutcome, SceneType

from tests.engine.judgments.builders import (
    CAPTIVE_ID,
    arm_manually,
    captive_pending,
    governor_pending,
    judgment_scenario,
    judgment_world,
)


def _armed(pending=None):
    world = judgment_world()
    scene_id = arm_manually(world, pending or captive_pending())
    return world, judgment_scenario(), scene_id


def test_closing_applies_the_verdict_and_clears_the_pending_scene() -> None:
    world, scenario, scene_id = _armed()
    closed, events = close_judgment(
        world, scenario, scene_id, JudgmentOutcome(verdict=JudgmentVerdict.RELEASE)
    )
    assert closed.prisoners == []
    assert closed.progress.pending_scene_id is None
    assert closed.progress.pending_judgment is None
    assert closed.progress.negotiation_counterpart_id is None
    assert [event.kind for event in events] == [
        "prisoner_released",
        "judgment_pronounced",
    ]
    assert world.progress.pending_judgment is not None


def test_closing_never_mutates_the_input_world() -> None:
    world, scenario, scene_id = _armed()
    before = world_hash(world)
    close_judgment(
        world, scenario, scene_id, JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE)
    )
    assert world_hash(world) == before


def test_closing_is_deterministic() -> None:
    first = _armed()
    second = _armed()
    outcome = JudgmentOutcome(
        verdict=JudgmentVerdict.EXECUTE, nuance=JudgmentNuance.PUBLICLY
    )
    closed_first, _ = close_judgment(*first, outcome)
    closed_second, _ = close_judgment(*second, outcome)
    assert world_hash(closed_first) == world_hash(closed_second)


def test_the_shared_close_scene_path_dispatches_judgments() -> None:
    world, scenario, scene_id = _armed(governor_pending())
    closed, _ = close_scene(
        world,
        scenario,
        SceneType.JUDGMENT,
        scene_id,
        JudgmentOutcome(verdict=JudgmentVerdict.EXILE),
    )
    assert closed.progress.pending_judgment is None
    assert closed.regions["ash_ford"].governor_id is None


def test_a_wrong_scene_id_is_not_found() -> None:
    world, scenario, _ = _armed()
    with pytest.raises(CampaignProgressError) as error:
        close_judgment(
            world,
            scenario,
            world.playthrough_id,
            JudgmentOutcome(verdict=JudgmentVerdict.RELEASE),
        )
    assert error.value.status_code == 404


def test_an_outcome_of_another_kind_is_invalid() -> None:
    world, scenario, scene_id = _armed()
    with pytest.raises(CampaignProgressError) as error:
        close_judgment(world, scenario, scene_id, ChoiceOutcome(option_id="release"))
    assert error.value.status_code == 422


def test_closing_a_stale_subject_clears_the_scene_and_applies_nothing() -> None:
    world, scenario, scene_id = _armed()
    world.prisoners = []
    closed, events = close_judgment(
        world, scenario, scene_id, JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE)
    )
    assert events == []
    assert closed.progress.pending_scene_id is None
    assert closed.player_profile.cruelty_acts == 0
    assert CAPTIVE_ID not in [item.id for item in closed.prisoners]


def test_closing_numbers_its_events_like_other_scene_closers() -> None:
    world, scenario, scene_id = _armed()
    world.siege_ruleset = 1
    closed, events = close_judgment(
        world, scenario, scene_id, JudgmentOutcome(verdict=JudgmentVerdict.RELEASE)
    )
    assert [event.seq for event in events] == [1, 2]
    assert {event.turn for event in events} == {world.clock.turn}
    assert closed.counters["event_seq"] == 2
