from app.engine.negotiation_decision import (
    REASON_NOT_ALLOWED,
    REASON_OUTSIDE_LIMITS,
    Interpretation,
)
from app.engine.peace.signing import is_term_signable
from app.engine.pressure.wars import find_war
from app.engine.treaty.ledger import evaluate_card
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ScenePackage, TermsCardOutcome, TermsResult
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import (
    CedeRegionTerm,
    HostageTerm,
    PayGoldTerm,
    PeaceTerm,
    ReleasePrisonersTerm,
    Term,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
)
from strategy_contracts.treaty import Verdict

REASON_MISSING_TIER = "missing_tier"
REASON_NO_WAR = "no_war"
REASON_INVALID_TERMS = "invalid_terms"
MODEL_TERM_TYPES = (PayGoldTerm, CedeRegionTerm)
TREATY_TERM_TYPES = (
    *MODEL_TERM_TYPES,
    TributeTerm,
    HostageTerm,
    ReleasePrisonersTerm,
    TradeDealTerm,
)


def _model_terms(decision: SceneDecision, world: WorldState) -> list[Term]:
    allowed = TREATY_TERM_TYPES if world.treaty_ruleset >= 1 else MODEL_TERM_TYPES
    return [term for term in decision.terms if isinstance(term, allowed)]


def _peace_card(
    decision: SceneDecision, world: WorldState, player_id: str, counterpart_id: str
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
        terms=[peace, *_model_terms(decision, world)],
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
    card = _peace_card(decision, world, player_id, counterpart_id)
    pair = {player_id, counterpart_id}
    if not all(is_term_signable(world, term, pair) for term in card.terms[1:]):
        return Interpretation(reason=REASON_INVALID_TERMS)
    judged = evaluate_card(world, scenario, card, war)
    if judged.verdict is not Verdict.ACCEPT:
        return Interpretation(
            reason=REASON_OUTSIDE_LIMITS, verdict=judged.verdict, bands=judged.bands
        )
    outcome = TermsCardOutcome(result=TermsResult.AGREED, terms_card=card)
    if validate_outcome_against_package(package, outcome):
        return Interpretation(reason=REASON_NOT_ALLOWED)
    return Interpretation(proposal=card, verdict=judged.verdict, bands=judged.bands)
