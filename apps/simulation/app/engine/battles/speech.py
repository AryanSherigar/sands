from app.engine.army_mood import reaction_from_delta
from app.engine.speech_grade import apply_speech_outcome
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.replay import SkipBattleSpeechReplayInput, SubmitSpeechTalkReplayInput
from app.models.world_battle import BattleSpeechState, BattleSpeechStatus, BattleState
from app.models.world_events import StateChange
from app.models.world_state import WorldState
from strategy_contracts.battle_speech import MAX_SPEECH_TALKS, CrowdReaction
from strategy_contracts.scene import BattleSpeechOutcome

TALKS_BEFORE_CLOSING = MAX_SPEECH_TALKS - 1
NEUTRAL_OUTCOME = BattleSpeechOutcome(morale_delta_percent=0)


def _find_battle(world: WorldState, battle_id: str) -> BattleState:
    battle = next((item for item in world.battles if item.id == battle_id), None)
    if battle is None:
        raise CampaignProgressError("battle unavailable", "not_found", 404)
    return battle


def _open_speech(world: WorldState, battle_id: str) -> BattleSpeechState:
    speech = _find_battle(world, battle_id).speech
    if speech is None or speech.status != BattleSpeechStatus.PENDING:
        raise CampaignProgressError("no speech is pending", "invalid_lifecycle")
    return speech


def player_army_ids(world: WorldState, battle: BattleState) -> list[str]:
    return sorted(
        army_id
        for faction_id, contingent in battle.contingents.items()
        if world.factions[faction_id].is_player
        for army_id in contingent.army_ids
    )


def complete_speech(
    world: WorldState, battle_id: str, outcome: BattleSpeechOutcome
) -> list[StateChange]:
    battle = _find_battle(world, battle_id)
    speech = battle.speech
    if speech is None or speech.status == BattleSpeechStatus.DONE:
        return []
    changes: list[StateChange] = []
    for army_id in player_army_ids(world, battle):
        changes.extend(apply_speech_outcome(world, army_id, outcome))
    speech.status = BattleSpeechStatus.DONE
    speech.outcome = outcome
    return changes


def record_speech_talk(
    world: WorldState, battle_id: str, text: str, reaction: CrowdReaction
) -> None:
    speech = _open_speech(world, battle_id)
    if len(speech.transcripts) >= TALKS_BEFORE_CLOSING:
        raise CampaignProgressError("the closing talk is next", "invalid_lifecycle")
    speech.transcripts.append(text)
    speech.reactions.append(reaction)


def finish_speech(
    world: WorldState, battle_id: str, text: str, outcome: BattleSpeechOutcome
) -> list[StateChange]:
    speech = _open_speech(world, battle_id)
    if len(speech.transcripts) != TALKS_BEFORE_CLOSING:
        raise CampaignProgressError("earlier talks come first", "invalid_lifecycle")
    speech.transcripts.append(text)
    speech.reactions.append(reaction_from_delta(outcome.morale_delta_percent))
    return complete_speech(world, battle_id, outcome)


def skip_speech(world: WorldState, battle_id: str) -> list[StateChange]:
    _open_speech(world, battle_id)
    return complete_speech(world, battle_id, NEUTRAL_OUTCOME)


def apply_speech_step(
    world: WorldState,
    replay_input: SubmitSpeechTalkReplayInput | SkipBattleSpeechReplayInput,
) -> WorldState:
    if isinstance(replay_input, SkipBattleSpeechReplayInput):
        skip_speech(world, replay_input.battle_id)
    elif replay_input.outcome is not None:
        finish_speech(
            world, replay_input.battle_id, replay_input.text, replay_input.outcome
        )
    elif replay_input.reaction is not None:
        record_speech_talk(
            world, replay_input.battle_id, replay_input.text, replay_input.reaction
        )
    return world
