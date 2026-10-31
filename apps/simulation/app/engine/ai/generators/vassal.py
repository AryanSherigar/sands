from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import war_enemies
from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.vassals.registry import granted_share, vassal_term, vassals_of
from app.models.orders import (
    AnnexVassalOrder,
    DemandFromVassalOrder,
    ReleaseVassalOrder,
)
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.vassal import DemandKind

CONQUEST_CATEGORIES = (ScoreCategory.EXPAND, ScoreCategory.ATTACK)


def _vassal_power_percent(
    world: WorldState,
    scenario: StrategyScenario,
    overlord_id: FactionId,
    vassal_id: FactionId,
) -> int:
    ratio = known_power_ratio(world, scenario, overlord_id, vassal_id)
    return FULL_PERCENT * FULL_PERCENT // max(ratio, 1)


def _grievance_of(world: WorldState, commitment: CommitmentState) -> int:
    return next(
        (
            item.grievance
            for item in world.vassal.standing
            if item.vassalage_id == commitment.id
        ),
        0,
    )


def _owned_vassalages(
    world: WorldState, faction_id: FactionId
) -> list[CommitmentState]:
    return [
        item
        for item in vassals_of(world, faction_id)
        if not world.factions[vassal_term(item).vassal_id].is_player
    ]


def _demand_kind(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> DemandKind:
    is_poor = world.factions[faction_id].treasury < scenario.tuning.ai.low_treasury
    if is_poor or not war_enemies(world, faction_id):
        return DemandKind.TRIBUTE
    return DemandKind.LEVY


def _demand_candidate(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    commitment: CommitmentState,
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    term = vassal_term(commitment)
    power = _vassal_power_percent(world, scenario, faction_id, term.vassal_id)
    if power >= scenario.tuning.vassal.rebel_min_power_percent:
        return []
    kind = _demand_kind(world, scenario, faction_id)
    amount = granted_share(commitment, kind) + tuning.demand_step_percent
    if amount > FULL_PERCENT:
        return []
    order = DemandFromVassalOrder(
        faction_id=faction_id,
        vassalage_id=commitment.id,
        demand_kind=kind,
        amount=amount,
    )
    return [Candidate(order, ScoreCategory.HOARD, tuning.demand_vassal_bonus)]


def _annex_candidate(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    commitment: CommitmentState,
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    aim = world.aims.get(faction_id)
    if aim is None or aim.category not in CONQUEST_CATEGORIES:
        return []
    term = vassal_term(commitment)
    power = _vassal_power_percent(world, scenario, faction_id, term.vassal_id)
    if power > tuning.annex_max_power_percent:
        return []
    order = AnnexVassalOrder(faction_id=faction_id, vassalage_id=commitment.id)
    return [Candidate(order, ScoreCategory.EXPAND, tuning.annex_bonus)]


def _is_release_wise(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    commitment: CommitmentState,
) -> bool:
    tuning = scenario.tuning.ai
    term = vassal_term(commitment)
    power = _vassal_power_percent(world, scenario, faction_id, term.vassal_id)
    is_restless = (
        _grievance_of(world, commitment) >= tuning.release_grievance
        and power >= scenario.tuning.vassal.rebel_min_power_percent
    )
    is_broke_at_war = world.factions[
        faction_id
    ].treasury < tuning.low_treasury and bool(war_enemies(world, faction_id))
    return is_restless or is_broke_at_war


def _release_candidate(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    commitment: CommitmentState,
) -> list[Candidate]:
    if not _is_release_wise(world, scenario, faction_id, commitment):
        return []
    order = ReleaseVassalOrder(faction_id=faction_id, vassalage_id=commitment.id)
    return [Candidate(order, ScoreCategory.BUILD, scenario.tuning.ai.release_bonus)]


def vassal_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    if not scenario.toggles.is_ai_vassal_enabled or world.vassal_ruleset < 1:
        return []
    candidates: list[Candidate] = []
    for commitment in _owned_vassalages(world, faction_id):
        candidates += _demand_candidate(world, scenario, faction_id, commitment)
        candidates += _annex_candidate(world, scenario, faction_id, commitment)
        candidates += _release_candidate(world, scenario, faction_id, commitment)
    return candidates
