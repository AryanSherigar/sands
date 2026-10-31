import pytest
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.outrage import OutrageTuning
from strategy_contracts.scenario import Tuning
from strategy_contracts.scene import RefusedDemand, TermsCardOutcome, TermsResult
from strategy_contracts.scene_exchange import (
    SceneAction,
    SceneDecision,
    SceneExchangeSubmission,
)
from strategy_contracts.terms import PayGoldTerm, TermsCard


def test_defaults_load_for_legacy_scenario() -> None:
    assert load_three_crowns().tuning.outrage == OutrageTuning()


def test_tuning_mounts_on_scenario_tuning() -> None:
    assert Tuning().outrage.rule_version == 1


def test_level_thresholds_must_strictly_increase() -> None:
    with pytest.raises(ValidationError):
        OutrageTuning(level_thresholds_percent=[50, 50, 100, 150])


def test_level_thresholds_need_one_entry_per_raised_level() -> None:
    with pytest.raises(ValidationError):
        OutrageTuning(level_thresholds_percent=[50, 100])


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        OutrageTuning.model_validate({"surprise": 1})


def _submission(**extra: int) -> SceneExchangeSubmission:
    return SceneExchangeSubmission(
        sequence=1,
        player_text="Kneel.",
        leader_text="Never.",
        decision=SceneDecision(action=SceneAction.REFUSE),
        **extra,
    )


def test_tone_grade_defaults_to_zero_for_recorded_journals() -> None:
    assert _submission().tone_grade == 0


def test_tone_grade_is_bounded() -> None:
    with pytest.raises(ValidationError):
        _submission(tone_grade=6)


def test_a_refused_demand_rides_on_the_terms_outcome() -> None:
    outcome = TermsCardOutcome(
        result=TermsResult.REFUSED,
        refused_demand=RefusedDemand(
            terms_card=TermsCard(
                proposer_id="f1",
                counterpart_id="f2",
                terms=[PayGoldTerm(payer_id="f2", payee_id="f1", amount=50)],
            ),
            tone_grade=4,
        ),
    )

    assert outcome.refused_demand is not None
    assert outcome.refused_demand.tone_grade == 4


def test_outcomes_without_a_refused_demand_still_load() -> None:
    assert TermsCardOutcome(result=TermsResult.AGREED).refused_demand is None
