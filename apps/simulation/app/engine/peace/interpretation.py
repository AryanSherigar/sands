from app.engine.negotiation_decision import (
    REASON_NOT_ALLOWED,
    REASON_OUTSIDE_LIMITS,
    Interpretation,
)
from app.engine.peace.acceptance import does_counterpart_accept
from app.engine.pressure.wars import find_war
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ScenePackage, TermsCardOutcome, TermsResult
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import PeaceTerm, TermsCard

REASON_MISSING_TIER = "missing_tier"
REASON_NO_WAR = "no_war"


def _peace_card(
    decision: SceneDecision, player_id: str, counterpart_id: str
) -> TermsCard:
    assert decision.peace_tier is not None
    peace = PeaceTerm(
        faction_a=player_id,
        faction_b=counterpart_id,
        tier=decision.peace_tier,
        guarantor_ids=list(decision.guarantor_ids),
        is_white_peace=decision.is_white_peace,
    )
    return TermsCard(
        proposer_id=player_id,
        counterpart_id=counterpart_id,
        terms=[peace, *decision.terms],
        is_confirmed_by_counterpart=True,
    )


def interpret_peace_decision(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
    player_id: str,
    counterpart_id: str,
) -> Interpretation:
    """Bound a proposed peace by affordability, the counterpart's acceptance line and the scene's allowed kinds."""
    if decision.action is SceneAction.WALK_OUT:
        return Interpretation(ending=TermsResult.WALKED_OUT)
    if decision.action is SceneAction.REFUSE:
        return Interpretation(ending=TermsResult.REFUSED)
    if decision.action is not SceneAction.PROPOSE_TERMS:
        return Interpretation()
    if decision.peace_tier is None:
        return Interpretation(reason=REASON_MISSING_TIER)
    war = find_war(world, player_id, counterpart_id)
    if war is None:
        return Interpretation(reason=REASON_NO_WAR)
    card = _peace_card(decision, player_id, counterpart_id)
    if not does_counterpart_accept(world, scenario, card, war):
        return Interpretation(reason=REASON_OUTSIDE_LIMITS)
    outcome = TermsCardOutcome(result=TermsResult.AGREED, terms_card=card)
    if validate_outcome_against_package(package, outcome):
        return Interpretation(reason=REASON_NOT_ALLOWED)
    return Interpretation(proposal=card)
