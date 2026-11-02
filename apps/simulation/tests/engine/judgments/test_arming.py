from uuid import UUID

from app.engine.hashing import world_hash
from app.engine.judgments.arming import arm_judgment, judgment_scene_id
from strategy_contracts.judgment import JudgmentSubjectKind

from tests.engine.judgments.builders import (
    CAPTIVE_ID,
    GOVERNOR_ID,
    RIVAL,
    TURN,
    judgment_scenario,
    judgment_world,
    uprising_event,
)


def test_arming_sets_scene_pending_judgment_counterpart_and_cooldown() -> None:
    world = judgment_world()
    arm_judgment(world, judgment_scenario(), [])
    pending = world.progress.pending_judgment
    assert pending is not None
    assert pending.subject_id == CAPTIVE_ID
    assert world.progress.pending_scene_id == judgment_scene_id(world, CAPTIVE_ID)
    assert world.progress.negotiation_counterpart_id == RIVAL
    assert world.judgment_cooldowns[CAPTIVE_ID] == TURN + 6


def test_the_scene_id_depends_on_playthrough_turn_and_subject() -> None:
    world = judgment_world()
    first = judgment_scene_id(world, CAPTIVE_ID)
    assert first == judgment_scene_id(world, CAPTIVE_ID)
    assert first != judgment_scene_id(world, GOVERNOR_ID)
    world.clock.turn += 1
    assert first != judgment_scene_id(world, CAPTIVE_ID)


def test_a_scenario_with_judgments_off_never_arms() -> None:
    world = judgment_world()
    arm_judgment(world, judgment_scenario(is_enabled=False), [])
    assert world.progress.pending_scene_id is None
    assert world.progress.pending_judgment is None


def test_no_judgment_is_armed_while_another_scene_is_pending() -> None:
    world = judgment_world()
    pending_scene = UUID(int=9)
    world.progress.pending_scene_id = pending_scene
    arm_judgment(world, judgment_scenario(), [])
    assert world.progress.pending_scene_id == pending_scene
    assert world.progress.pending_judgment is None
    assert world.judgment_cooldowns == {}


def test_nothing_arms_when_there_is_no_eligible_subject() -> None:
    world = judgment_world()
    world.prisoners = []
    arm_judgment(world, judgment_scenario(), [])
    assert world.progress.pending_scene_id is None


def test_with_several_candidates_exactly_one_arms_the_lowest_sorted() -> None:
    world = judgment_world()
    world.prisoners.append(
        world.prisoners[0].model_copy(
            update={"id": "captive_0", "character_id": "ser_zed"}
        )
    )
    arm_judgment(world, judgment_scenario(), [uprising_event("uprising_crushed")])
    pending = world.progress.pending_judgment
    assert pending is not None
    assert pending.subject_id == "captive_0"
    assert set(world.judgment_cooldowns) == {"captive_0"}


def test_the_losing_candidates_arm_on_later_turns() -> None:
    world = judgment_world()
    scenario = judgment_scenario()
    event = uprising_event("uprising_crushed")
    arm_judgment(world, scenario, [event])
    assert world.progress.pending_judgment.subject_kind is JudgmentSubjectKind.CAPTIVE
    world.progress.pending_scene_id = None
    world.progress.pending_judgment = None
    arm_judgment(world, scenario, [event])
    assert world.progress.pending_judgment.subject_id == GOVERNOR_ID


def test_arming_is_deterministic_for_replay() -> None:
    first, second = judgment_world(), judgment_world()
    events = [uprising_event("uprising_crushed")]
    arm_judgment(first, judgment_scenario(), events)
    arm_judgment(second, judgment_scenario(), events)
    assert world_hash(first) == world_hash(second)
