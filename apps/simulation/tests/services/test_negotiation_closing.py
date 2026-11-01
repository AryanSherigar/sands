from app.services.negotiation_closing import attach_refused_demand, build_outcome
from strategy_contracts.scene import SceneStatus, TermsCardOutcome, TermsResult
from strategy_contracts.terms import PayGoldTerm, TermsCard

PROPOSAL = TermsCard(
    proposer_id="f1",
    counterpart_id="f2",
    terms=[PayGoldTerm(payer_id="f2", payee_id="f1", amount=50)],
)
TONE = 4


def _attach(result: TermsResult, status: SceneStatus, proposal: TermsCard | None):
    outcome, _ = attach_refused_demand(
        build_outcome(result, None), status, proposal, TONE
    )
    assert isinstance(outcome, TermsCardOutcome)
    return outcome


def test_an_explicit_refusal_carries_the_demand_and_tone() -> None:
    outcome = _attach(TermsResult.REFUSED, SceneStatus.RESOLVED, PROPOSAL)

    assert outcome.refused_demand is not None
    assert outcome.refused_demand.terms_card == PROPOSAL
    assert outcome.refused_demand.tone_grade == TONE


def test_a_walk_out_carries_the_demand_too() -> None:
    outcome = _attach(TermsResult.WALKED_OUT, SceneStatus.RESOLVED, PROPOSAL)

    assert outcome.refused_demand is not None


def test_a_defaulted_scene_angers_nobody() -> None:
    outcome = _attach(TermsResult.WALKED_OUT, SceneStatus.DEFAULTED, PROPOSAL)

    assert outcome.refused_demand is None


def test_a_refusal_with_nothing_on_the_table_has_no_demand() -> None:
    outcome = _attach(TermsResult.REFUSED, SceneStatus.RESOLVED, None)

    assert outcome.refused_demand is None
