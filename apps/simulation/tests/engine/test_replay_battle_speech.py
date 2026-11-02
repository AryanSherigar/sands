import pytest
from app.engine.battles.speech import finish_speech, record_speech_talk, skip_speech
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.battle_progress import OperationGuard
from app.models.replay import (
    ReplayStep,
    SkipBattleSpeechReplayInput,
    SubmitSpeechTalkReplayInput,
)
from app.models.world_state import WorldState
from strategy_contracts.battle_speech import CrowdMood, CrowdReaction
from strategy_contracts.scene import BattleSpeechOutcome

from tests.engine.battles.test_battle_speech_state import take_command

CHEER = CrowdReaction(mood=CrowdMood.CHEER, intensity=2)


def guard(name: str) -> OperationGuard:
    return OperationGuard(
        operation_id=name, expected_world_version=1, expected_turn=0, expected_wave=1
    )


def step_after(
    world: WorldState,
    sequence: int,
    replay_input: SubmitSpeechTalkReplayInput | SkipBattleSpeechReplayInput,
    before: str,
) -> ReplayStep:
    return ReplayStep(
        playthrough_id=world.playthrough_id,
        sequence=sequence,
        operation_id=replay_input.guard.operation_id,
        kind=replay_input.kind,
        input=replay_input,
        before_hash=before,
        after_hash=world_hash(world),
        turn=world.clock.turn,
        wave=world.progress.completed_waves,
    )


def recorded_three_talk_speech() -> tuple[
    WorldState, list[ReplayStep], WorldState, object
]:
    initial, scenario = take_command(speech_ruleset=1)
    world = initial.model_copy(deep=True)
    steps: list[ReplayStep] = []
    outcome = BattleSpeechOutcome(morale_delta_percent=7)
    inputs = [
        SubmitSpeechTalkReplayInput(
            guard=guard("t1"), battle_id="battle_1", text="One", reaction=CHEER
        ),
        SubmitSpeechTalkReplayInput(
            guard=guard("t2"), battle_id="battle_1", text="Two", reaction=CHEER
        ),
        SubmitSpeechTalkReplayInput(
            guard=guard("t3"), battle_id="battle_1", text="Closing", outcome=outcome
        ),
    ]
    for sequence, replay_input in enumerate(inputs, start=1):
        before = world_hash(world)
        if replay_input.outcome is None:
            record_speech_talk(world, "battle_1", replay_input.text, CHEER)
        else:
            finish_speech(world, "battle_1", replay_input.text, outcome)
        steps.append(step_after(world, sequence, replay_input, before))
    return initial, steps, world, scenario


def test_a_three_talk_speech_replays_to_the_same_hash() -> None:
    initial, steps, final, scenario = recorded_three_talk_speech()
    result = replay_history(initial, scenario, steps)
    assert result.world_hash == world_hash(final)
    assert result.step_count == 3


def test_a_skipped_speech_replays_to_the_same_hash() -> None:
    initial, scenario = take_command(speech_ruleset=1)
    world = initial.model_copy(deep=True)
    before = world_hash(world)
    skip_speech(world, "battle_1")
    replay_input = SkipBattleSpeechReplayInput(
        guard=guard("skip"), battle_id="battle_1"
    )
    steps = [step_after(world, 1, replay_input, before)]
    assert replay_history(initial, scenario, steps).world_hash == world_hash(world)


def test_a_tampered_reaction_is_caught_by_the_hash_check() -> None:
    initial, steps, _, scenario = recorded_three_talk_speech()
    tampered = steps[0].model_copy(deep=True)
    tampered.input.reaction = CrowdReaction(mood=CrowdMood.PROTEST, intensity=3)
    with pytest.raises(ReplayMismatchError):
        replay_history(initial, scenario, [tampered, *steps[1:]])


def test_a_talk_step_needs_exactly_one_of_reaction_or_outcome() -> None:
    with pytest.raises(ValueError):
        SubmitSpeechTalkReplayInput(guard=guard("bad"), battle_id="b", text="x")
    with pytest.raises(ValueError):
        SubmitSpeechTalkReplayInput(
            guard=guard("bad"),
            battle_id="b",
            text="x",
            reaction=CHEER,
            outcome=BattleSpeechOutcome(morale_delta_percent=1),
        )
