from app.engine.ai.candidates import Candidate
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_internal import UprisingResponse, allowed_responses
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

RESPONSE_CATEGORY: dict[UprisingResponse, ScoreCategory] = {
    UprisingResponse.CONCESSIONS: ScoreCategory.BUILD,
    UprisingResponse.RESTORE_ORDER: ScoreCategory.ATTACK,
    UprisingResponse.NEGOTIATE: ScoreCategory.ALLY,
}


def uprising_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    bonus = scenario.tuning.ai.uprising_bonus
    return [
        Candidate(
            ResolveUprisingCommand(
                faction_id=faction_id, uprising_id=uprising.id, response=response
            ),
            RESPONSE_CATEGORY[response],
            bonus,
        )
        for uprising in sorted(world.uprisings, key=lambda item: item.id)
        if uprising.faction_id == faction_id
        for response in sorted(allowed_responses(uprising), key=lambda item: item.value)
    ]
