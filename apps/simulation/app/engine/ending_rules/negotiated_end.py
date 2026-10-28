from app.engine.negotiation import player_faction_id
from app.models.world_diplomacy import TruceState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def _is_lasting_guarantee(truce: TruceState, world: WorldState, min_turns: int) -> bool:
    if not truce.guarantor_ids:
        return False
    # NOTE: expires_turn 0 marks a truce with no expiry.
    if truce.expires_turn == 0:
        return True
    return truce.expires_turn - world.clock.turn >= min_turns


def is_negotiated_end(world: WorldState, scenario: StrategyScenario) -> bool:
    if not world.endings.has_seen_war or world.wars:
        return False
    player_id = player_faction_id(world)
    min_turns = scenario.tuning.endings.negotiated_min_truce_turns
    return any(
        player_id in {truce.faction_a, truce.faction_b}
        and _is_lasting_guarantee(truce, world, min_turns)
        for truce in world.truces
    )
