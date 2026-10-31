from app.engine.negotiation_decision import (
    REASON_MISSING_DURATION,
    REASON_NOT_ALLOWED,
    Interpretation,
)
from app.engine.treaty.ledger import evaluate_card
from app.engine.treaty.registry import term_parties
from app.engine.treaty.signing import validate_card
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    ScenePackage,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import (
    ConditionalTerm,
    MilitaryAccessTerm,
    NonAggressionTerm,
    SwornPromiseTerm,
    Term,
    TermKind,
    TermsCard,
    TradeDealTerm,
)
from strategy_contracts.treaty import Verdict

REASON_INVALID_TERMS = "invalid_terms"
TIMED_TERMS = (NonAggressionTerm, TradeDealTerm, MilitaryAccessTerm, SwornPromiseTerm)


def _terms_spec(package: ScenePackage) -> TermsCardSpec:
    default = TermsCardSpec(allowed_term_kinds=[TermKind.NON_AGGRESSION])
    return next(
        (item for item in package.allowed_outcomes if isinstance(item, TermsCardSpec)),
        default,
    )


def _clamp(term: Term, max_turns: int) -> Term:
    if isinstance(term, ConditionalTerm):
        return term.model_copy(update={"inner": _clamp(term.inner, max_turns)})
    if isinstance(term, TIMED_TERMS) and term.duration_turns > max_turns:
        return term.model_copy(update={"duration_turns": max_turns})
    return term


def _flat_clauses(
    decision: SceneDecision, player_id: str, counterpart_id: str, max_turns: int
) -> list[Term]:
    if decision.duration_turns is None:
        return []
    duration = min(decision.duration_turns, max_turns)
    if decision.promise_kind is None:
        return [
            NonAggressionTerm(
                faction_a=player_id, faction_b=counterpart_id, duration_turns=duration
            )
        ]
    promisor_id, beneficiary_id = player_id, counterpart_id
    if decision.is_promise_by_ruler:
        promisor_id, beneficiary_id = counterpart_id, player_id
    return [
        SwornPromiseTerm(
            promisor_id=promisor_id,
            beneficiary_id=beneficiary_id,
            promise=decision.promise_kind,
            subject_id=decision.promise_subject_id,
            duration_turns=duration,
        )
    ]


def _clauses(
    decision: SceneDecision, player_id: str, counterpart_id: str, max_turns: int
) -> list[Term]:
    modelled = [_clamp(term, max_turns) for term in decision.terms]
    return [*modelled, *_flat_clauses(decision, player_id, counterpart_id, max_turns)]


def _is_between(terms: list[Term], player_id: str, counterpart_id: str) -> bool:
    pair = {player_id, counterpart_id}
    return all(term_parties(term) == pair for term in terms)


def _is_signable(
    world: WorldState, scenario: StrategyScenario, card: TermsCard
) -> bool:
    try:
        validate_card(world, scenario, card)
    except CampaignProgressError:
        return False
    return True


def _judge(
    card: TermsCard,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> Interpretation:
    outcome = TermsCardOutcome(result=TermsResult.AGREED, terms_card=card)
    if validate_outcome_against_package(package, outcome):
        return Interpretation(reason=REASON_NOT_ALLOWED)
    result = evaluate_card(world, scenario, card, None)
    if result.verdict is not Verdict.ACCEPT:
        return Interpretation(
            reason=result.reason, verdict=result.verdict, bands=result.bands
        )
    if not _is_signable(world, scenario, card):
        return Interpretation(reason=REASON_INVALID_TERMS)
    return Interpretation(proposal=card, verdict=result.verdict, bands=result.bands)


def _propose(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
    player_id: str,
    counterpart_id: str,
) -> Interpretation:
    max_turns = _terms_spec(package).max_duration_turns
    clauses = _clauses(decision, player_id, counterpart_id, max_turns)
    if not clauses:
        return Interpretation(reason=REASON_MISSING_DURATION)
    if not _is_between(clauses, player_id, counterpart_id):
        return Interpretation(reason=REASON_INVALID_TERMS)
    card = TermsCard(
        proposer_id=player_id,
        counterpart_id=counterpart_id,
        terms=clauses,
        is_confirmed_by_counterpart=True,
    )
    return _judge(card, package, world, scenario)


def interpret_card_decision(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
    player_id: str,
    counterpart_id: str,
) -> Interpretation:
    """Price a model-proposed multi-clause card through the shared treaty ledger."""
    if decision.action is SceneAction.WALK_OUT:
        return Interpretation(ending=TermsResult.WALKED_OUT)
    if decision.action is SceneAction.REFUSE:
        return Interpretation(ending=TermsResult.REFUSED)
    if decision.action is not SceneAction.PROPOSE_TERMS:
        return Interpretation()
    return _propose(decision, package, world, scenario, player_id, counterpart_id)
