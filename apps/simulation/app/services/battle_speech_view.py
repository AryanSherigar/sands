from app.engine.army_mood import army_mood, officer_report
from app.engine.battles.speech import player_army_ids
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.api_battle_speech import SpeechView
from app.models.world_battle import BattleSpeechStatus, BattleState
from app.models.world_state import WorldState
from strategy_contracts.battle_speech import MAX_SPEECH_TALKS

DEFAULT_OFFICER_NAME = "Your captain"


def find_battle_with_speech(world: WorldState, battle_id: str) -> BattleState:
    battle = next((item for item in world.battles if item.id == battle_id), None)
    if battle is None or battle.speech is None:
        raise CampaignProgressError("speech unavailable", "not_found", 404)
    return battle


def speech_army_id(world: WorldState, battle: BattleState) -> str:
    army_ids = player_army_ids(world, battle)
    if not army_ids:
        raise CampaignProgressError("speech unavailable", "not_found", 404)
    return army_ids[0]


def _officer_name(world: WorldState, army_id: str) -> str:
    commander_id = world.armies[army_id].commander_id
    commander = world.commanders.get(commander_id) if commander_id else None
    return commander.name if commander is not None else DEFAULT_OFFICER_NAME


def _next_talk(battle: BattleState) -> int | None:
    speech = battle.speech
    if speech is None or speech.status == BattleSpeechStatus.DONE:
        return None
    given = len(speech.transcripts)
    return given + 1 if given < MAX_SPEECH_TALKS else None


def build_speech_view(world: WorldState, battle_id: str) -> SpeechView:
    battle = find_battle_with_speech(world, battle_id)
    army_id = speech_army_id(world, battle)
    mood = army_mood(world.armies[army_id])
    speech = battle.speech
    return SpeechView(
        status=speech.status,
        officer_report=officer_report(mood, _officer_name(world, army_id)),
        mood=mood,
        next_talk=_next_talk(battle),
        reactions=list(speech.reactions),
        outcome=speech.outcome,
    )
