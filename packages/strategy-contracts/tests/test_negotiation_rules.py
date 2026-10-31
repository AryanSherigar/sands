import pytest
from pydantic import ValidationError
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.negotiation_rules import NegotiationRules, NegotiationTrigger
from strategy_contracts.publish_checks import IssueCode, check_publishable
from strategy_contracts.terms import TermKind


def _turn_trigger(**overrides: object) -> dict[str, object]:
    return {
        "id": "early_offer",
        "initiator_faction_id": "house_mira",
        "condition": Comparison(
            metric=ConditionMetric.TURN, operator=ConditionOperator.GTE, value=3
        ),
    } | overrides


def test_default_rules_keep_the_legacy_pact_pricing() -> None:
    rules = NegotiationRules()
    assert rules.allowed_term_kinds == [TermKind.NON_AGGRESSION]
    assert (rules.base_accept, rules.pact_value_per_turn) == (20, 6)
    assert rules.triggers == []


def test_every_term_kind_is_priced() -> None:
    assert NegotiationRules(allowed_term_kinds=[TermKind.TRIBUTE]).allowed_term_kinds


def test_trigger_defaults_to_declinable() -> None:
    trigger = NegotiationTrigger.model_validate(_turn_trigger())
    assert trigger.is_declinable is True


def test_trigger_rejects_unsupported_metric() -> None:
    condition = Comparison(
        metric=ConditionMetric.IS_RULER_ALIVE, operator=ConditionOperator.EQ, value=1
    )
    with pytest.raises(ValidationError):
        NegotiationTrigger.model_validate(_turn_trigger(condition=condition))


def test_trigger_with_unknown_faction_blocks_publish() -> None:
    scenario = load_three_crowns()
    trigger = NegotiationTrigger.model_validate(
        _turn_trigger(initiator_faction_id="nobody")
    )
    scenario.negotiation = NegotiationRules(triggers=[trigger])
    report = check_publishable(scenario)
    assert IssueCode.DANGLING_REFERENCE in {issue.code for issue in report.blocking}
