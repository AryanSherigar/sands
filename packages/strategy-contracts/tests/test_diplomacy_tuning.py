import pytest
from pydantic import ValidationError
from strategy_contracts.diplomacy import DiplomacyTuning, ScoreSource
from strategy_contracts.enums import OrderKind
from strategy_contracts.scenario import Tuning


def test_defaults_match_spec() -> None:
    tuning = Tuning().diplomacy

    assert tuning.war_score_cap == 100
    assert tuning.goal_slot_thresholds == [40, 70]


def test_order_costs_follow_spec() -> None:
    costs = Tuning().order_costs

    assert costs[OrderKind.DECLARE_WAR] == 2
    assert costs[OrderKind.CALL_NEGOTIATION] == 2
    assert costs[OrderKind.FABRICATE_CLAIM] == 2
    assert costs[OrderKind.DIPLOMATIC_PLAY] == 1


def test_score_weights_cover_every_source() -> None:
    assert set(DiplomacyTuning().score_weights) == set(ScoreSource)


def test_rejects_threshold_inversion() -> None:
    with pytest.raises(ValidationError):
        DiplomacyTuning(act_threshold_min=90)


def test_stored_order_costs_missing_new_kinds_fall_back_to_defaults() -> None:
    legacy = {kind.value: 1 for kind in OrderKind if kind != OrderKind.DECLARE_WAR}

    tuning = Tuning.model_validate({"order_costs": legacy})

    assert tuning.order_costs[OrderKind.DECLARE_WAR] == 2
    assert tuning.order_costs[OrderKind.MOVE_ARMY] == 1


def test_order_costs_cover_the_subsidy_orders() -> None:
    costs = Tuning().order_costs

    assert costs[OrderKind.SUBSIDIZE] == 1
    assert costs[OrderKind.CUT_SUBSIDY] == 1
