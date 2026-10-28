from app.models.speech_grading import SpeechBriefing
from app.models.world_state import WorldState
from app.services.trait_notes import trait_notes
from strategy_contracts.scenario import StrategyScenario


def build_speech_briefing(
    world: WorldState, scenario: StrategyScenario, army_id: str, speech_text: str
) -> SpeechBriefing:
    ruler = world.ruler
    army = world.armies[army_id]
    ambitions = {item.id: item.name for item in scenario.ambitions}
    return SpeechBriefing(
        speech_text=speech_text,
        ruler_name=ruler.name,
        ruler_epithet=ruler.epithet,
        ruler_trait_notes=trait_notes(ruler.trait_ids, scenario),
        ruler_ambitions=[ambitions.get(item, item) for item in ruler.ambition_ids],
        troop_count=sum(army.troops.values()),
        army_morale=army.morale,
        army_fatigue=army.fatigue,
        unpaid_turns=army.unpaid_turns,
    )
