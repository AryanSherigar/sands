from strategy_contracts.negotiation_rules import NegotiationRules
from strategy_contracts.scenario import Tuning
from strategy_contracts.scene_exchange import SceneExchangeResult
from strategy_contracts.terms import TermKind
from strategy_contracts.treaty import TreatyTuning, Verdict, WeightBand


def test_treaty_tuning_defaults() -> None:
    tuning = Tuning().treaty

    assert isinstance(tuning, TreatyTuning)
    assert (
        tuning.trade_value_per_turn,
        tuning.trade_income_percent,
        tuning.access_value_per_turn,
    ) == (4, 10, 2)


def test_all_term_kinds_are_allowed_in_rules() -> None:
    kinds = [TermKind.TRADE_DEAL, TermKind.MILITARY_ACCESS, TermKind.TRIBUTE]

    assert NegotiationRules(allowed_term_kinds=kinds).allowed_term_kinds == kinds


def test_exchange_result_defaults_carry_no_verdict() -> None:
    assert SceneExchangeResult.model_fields["verdict"].default is None
    assert SceneExchangeResult.model_fields["clause_bands"].default_factory() == []


def test_verdict_and_band_members() -> None:
    assert [item.value for item in Verdict] == ["accept", "haggle", "refuse"]
    assert [item.value for item in WeightBand] == ["light", "moderate", "heavy"]
