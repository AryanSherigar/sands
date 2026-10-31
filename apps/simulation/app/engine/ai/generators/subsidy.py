from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import war_enemies
from app.engine.pressure.wars import opposing_ids
from app.models.orders import CutSubsidyOrder, SubsidizeOrder
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

SURPLUS_TREASURY_MULTIPLE = 2


def _participants(war: WarState) -> set[FactionId]:
    return {war.attacker_id, war.defender_id, *war.participant_ids}


def _receivers(
    world: WorldState, faction_id: FactionId, war: WarState
) -> list[FactionId]:
    enemies = set(war_enemies(world, faction_id))
    return sorted(
        (
            other_id
            for other_id in _participants(war)
            if other_id != faction_id
            and other_id not in enemies
            and not world.factions[other_id].is_player
            and not world.factions[other_id].is_destroyed
            and enemies & set(opposing_ids(war, other_id))
        ),
        key=lambda other_id: (world.factions[other_id].treasury, other_id),
    )


def _surplus(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    tuning = scenario.tuning.ai
    floor = SURPLUS_TREASURY_MULTIPLE * tuning.low_treasury
    return world.factions[faction_id].treasury - floor


def _pay_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    turns = min(tuning.subsidy_turns, scenario.tuning.pressure.subsidy_max_turns)
    amount = min(
        scenario.tuning.pressure.subsidy_max_per_turn,
        _surplus(world, scenario, faction_id) // turns,
    )
    if amount < 1:
        return []
    candidates: list[Candidate] = []
    for war in world.wars:
        receivers = _receivers(world, faction_id, war)
        if not receivers:
            continue
        order = SubsidizeOrder(
            faction_id=faction_id,
            target_faction_id=receivers[0],
            war_id=war.id,
            amount_per_turn=amount,
            turns=turns,
        )
        candidates.append(Candidate(order, ScoreCategory.ALLY, tuning.subsidy_bonus))
    return candidates


def _cut_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    is_poor = world.factions[faction_id].treasury < tuning.low_treasury
    live_war_ids = {war.id for war in world.wars}
    return [
        Candidate(
            CutSubsidyOrder(faction_id=faction_id, subsidy_id=subsidy.id),
            ScoreCategory.HOARD,
            tuning.situation_bonus,
        )
        for subsidy in world.pressure.subsidies
        if subsidy.payer_id == faction_id
        and (is_poor or subsidy.war_id not in live_war_ids)
    ]


def subsidy_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    if not scenario.toggles.is_ai_subsidy_enabled:
        return []
    return _pay_candidates(world, scenario, faction_id) + _cut_candidates(
        world, scenario, faction_id
    )
