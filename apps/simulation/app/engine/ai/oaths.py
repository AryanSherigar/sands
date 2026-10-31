from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm
from strategy_contracts.traits import TraitAxis


def _has_oath_against(
    world: WorldState, faction_id: FactionId, target_id: FactionId
) -> bool:
    return any(
        commitment.status is CommitmentStatus.ACTIVE
        and isinstance(commitment.term, SwornPromiseTerm)
        and commitment.term.promise is PromiseKind.NEVER_ATTACK_FACTION
        and (commitment.term.promisor_id, commitment.term.beneficiary_id)
        == (faction_id, target_id)
        for commitment in world.commitments
    )


def oath_penalty(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    target_id: FactionId,
) -> int | None:
    """Score penalty for attacking an oath-protected target; None means the leader never would."""
    if not _has_oath_against(world, faction_id, target_id):
        return 0
    tuning = scenario.tuning.ai
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    honor = axis_totals(leader, scenario)[TraitAxis.HONOR] if leader else 0
    if honor >= tuning.oath_honor_threshold:
        return None
    return tuning.oath_break_penalty
