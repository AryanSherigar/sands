import pytest
from app.engine.battles.speech import finish_speech, record_speech_talk, skip_speech
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_battle import BattleSpeechStatus
from app.models.world_state import WorldState
from strategy_contracts.battle_speech import CrowdMood, CrowdReaction
from strategy_contracts.scene import BattleSpeechOutcome

from tests.engine.battles.builders import ATTACKER
from tests.engine.battles.test_battle_speech_state import take_command

MURMUR = CrowdReaction(mood=CrowdMood.MURMUR, intensity=1)
CHEER = CrowdReaction(mood=CrowdMood.CHEER, intensity=2)


def speech_world() -> WorldState:
    world, _ = take_command(speech_ruleset=1)
    return world


def player_morale(world: WorldState) -> int:
    army_id = world.battles[0].contingents[ATTACKER].army_ids[0]
    return world.armies[army_id].morale


def test_record_talk_appends_transcript_and_reaction() -> None:
    world = speech_world()
    record_speech_talk(world, "battle_1", "First talk", MURMUR)
    speech = world.battles[0].speech
    assert speech.transcripts == ["First talk"]
    assert speech.reactions == [MURMUR]
    assert speech.status == BattleSpeechStatus.PENDING


def test_record_talk_leaves_morale_untouched() -> None:
    world = speech_world()
    before = player_morale(world)
    record_speech_talk(world, "battle_1", "First talk", CHEER)
    assert player_morale(world) == before


def test_third_talk_requires_two_earlier_talks() -> None:
    world = speech_world()
    outcome = BattleSpeechOutcome(morale_delta_percent=5)
    with pytest.raises(CampaignProgressError):
        finish_speech(world, "battle_1", "Closing", outcome)


def test_a_third_recorded_talk_is_rejected() -> None:
    world = speech_world()
    record_speech_talk(world, "battle_1", "One", MURMUR)
    record_speech_talk(world, "battle_1", "Two", MURMUR)
    with pytest.raises(CampaignProgressError):
        record_speech_talk(world, "battle_1", "Three", MURMUR)


def test_finish_speech_applies_morale_once_and_derives_the_closing_reaction() -> None:
    world = speech_world()
    before = player_morale(world)
    record_speech_talk(world, "battle_1", "One", MURMUR)
    record_speech_talk(world, "battle_1", "Two", CHEER)
    finish_speech(
        world, "battle_1", "Closing", BattleSpeechOutcome(morale_delta_percent=-15)
    )
    speech = world.battles[0].speech
    assert speech.status == BattleSpeechStatus.DONE
    assert speech.transcripts == ["One", "Two", "Closing"]
    assert speech.reactions[-1] == CrowdReaction(mood=CrowdMood.PROTEST, intensity=3)
    assert player_morale(world) == max(before - 15, 0)


def test_skip_marks_the_speech_done_with_a_zero_swing() -> None:
    world = speech_world()
    before = player_morale(world)
    skip_speech(world, "battle_1")
    speech = world.battles[0].speech
    assert speech.status == BattleSpeechStatus.DONE
    assert speech.outcome == BattleSpeechOutcome(morale_delta_percent=0)
    assert player_morale(world) == before


def test_a_finished_speech_accepts_no_more_talks() -> None:
    world = speech_world()
    skip_speech(world, "battle_1")
    with pytest.raises(CampaignProgressError):
        record_speech_talk(world, "battle_1", "Late", MURMUR)


def test_a_battle_without_a_speech_rejects_talks() -> None:
    world, _ = take_command(speech_ruleset=0)
    with pytest.raises(CampaignProgressError):
        record_speech_talk(world, "battle_1", "Nobody listens", MURMUR)
