from app.engine.ai.candidates import Candidate
from app.engine.ai.generators.diplomacy import usable_grounds
from app.engine.alliances.registry import active_alliances, alliance_term
from app.models.orders import DenounceAllianceOrder
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory


def denounce_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    if not scenario.toggles.is_ai_alliance_enabled or world.alliance_ruleset < 1:
        return []
    aim = world.aims.get(faction_id)
    if aim is None or aim.target_faction_id is None:
        return []
    candidates: list[Candidate] = []
    for alliance in active_alliances(world, faction_id):
        term = alliance_term(alliance)
        partner_id = term.faction_b if term.faction_a == faction_id else term.faction_a
        if partner_id != aim.target_faction_id:
            continue
        if not usable_grounds(world, scenario, faction_id, partner_id):
            continue
        order = DenounceAllianceOrder(faction_id=faction_id, alliance_id=alliance.id)
        candidates.append(
            Candidate(order, ScoreCategory.ATTACK, scenario.tuning.ai.denounce_bonus)
        )
    return candidates
