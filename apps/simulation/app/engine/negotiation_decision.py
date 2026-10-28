from dataclasses import dataclass

from app.engine.negotiation import (
    PACT_VALUE_PER_TURN,
    OfferReaction,
    react_to_pact,
)
from strategy_contracts.scene import (
    ScenePackage,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import NonAggressionTerm, TermKind, TermsCard

REASON_MISSING_DURATION = "missing_duration"
REASON_OUTSIDE_LIMITS = "outside_limits"
REASON_NOT_ALLOWED = "not_allowed"
REASON_NO_LIMITS = "no_limits"


@dataclass(frozen=True)
class Interpretation:
    proposal: TermsCard | None = None
    ending: TermsResult | None = None
    reason: str | None = None


def _pact_card(
    player_faction_id: str, counterpart_faction_id: str, duration_turns: int
) -> TermsCard:
    return TermsCard(
        proposer_id=player_faction_id,
        counterpart_id=counterpart_faction_id,
        terms=[
            NonAggressionTerm(
                faction_a=player_faction_id,
                faction_b=counterpart_faction_id,
                duration_turns=duration_turns,
            )
        ],
        is_confirmed_by_counterpart=True,
    )


def _terms_spec(package: ScenePackage) -> TermsCardSpec:
    default = TermsCardSpec(allowed_term_kinds=[TermKind.NON_AGGRESSION])
    return next(
        (item for item in package.allowed_outcomes if isinstance(item, TermsCardSpec)),
        default,
    )


def _interpret_proposal(
    decision: SceneDecision,
    package: ScenePackage,
    player_faction_id: str,
    counterpart_faction_id: str,
) -> Interpretation:
    limits = package.hidden_limits.acceptance if package.hidden_limits else None
    if decision.duration_turns is None:
        return Interpretation(reason=REASON_MISSING_DURATION)
    if limits is None:
        return Interpretation(reason=REASON_NO_LIMITS)
    spec = _terms_spec(package)
    duration = min(decision.duration_turns, spec.max_duration_turns)
    price = spec.price_by_term_kind.get(TermKind.NON_AGGRESSION, PACT_VALUE_PER_TURN)
    reaction = react_to_pact(limits, duration, price, spec.max_duration_turns)
    if reaction is not OfferReaction.ACCEPT:
        return Interpretation(reason=REASON_OUTSIDE_LIMITS)
    card = _pact_card(player_faction_id, counterpart_faction_id, duration)
    outcome = TermsCardOutcome(result=TermsResult.AGREED, terms_card=card)
    if validate_outcome_against_package(package, outcome):
        return Interpretation(reason=REASON_NOT_ALLOWED)
    return Interpretation(proposal=card)


def interpret_decision(
    decision: SceneDecision,
    package: ScenePackage,
    player_faction_id: str,
    counterpart_faction_id: str,
) -> Interpretation:
    """Bound the model's proposed step by the hidden limits and the allowed outcomes."""
    if decision.action is SceneAction.WALK_OUT:
        return Interpretation(ending=TermsResult.WALKED_OUT)
    if decision.action is SceneAction.REFUSE:
        return Interpretation(ending=TermsResult.REFUSED)
    if decision.action is SceneAction.PROPOSE_TERMS:
        return _interpret_proposal(
            decision, package, player_faction_id, counterpart_faction_id
        )
    return Interpretation()
