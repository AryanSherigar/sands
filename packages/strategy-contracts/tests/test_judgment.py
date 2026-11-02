from uuid import uuid4

import pytest
from pydantic import ValidationError
from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    AdvisorStance,
    JudgmentNuance,
    JudgmentOption,
    JudgmentOutcome,
    JudgmentSpec,
    JudgmentSubjectKind,
    JudgmentTuning,
    JudgmentVerdict,
)
from strategy_contracts.scenario import Tuning
from strategy_contracts.scene import (
    Participant,
    ParticipantKind,
    ScenePackage,
    SceneSituation,
    SceneType,
)
from strategy_contracts.scene_exchange import SceneDecision
from strategy_contracts.scene_validation import (
    validate_outcome_against_package,
    validate_package,
)


def _spec() -> JudgmentSpec:
    return JudgmentSpec(
        subject_kind=JudgmentSubjectKind.CAPTIVE,
        options=[
            JudgmentOption(verdict=verdict, nuances=list(NUANCES_BY_VERDICT[verdict]))
            for verdict in JudgmentVerdict
        ],
    )


def _package(spec: JudgmentSpec) -> ScenePackage:
    return ScenePackage(
        scene_id=uuid4(),
        playthrough_id=uuid4(),
        scene_type=SceneType.JUDGMENT,
        turn=3,
        situation=SceneSituation(summary="A noble stands accused."),
        participants=[],
        allowed_outcomes=[spec],
        exchange_cap=6,
        default_outcome=JudgmentOutcome(verdict=JudgmentVerdict.IMPRISON),
    )


def test_nuance_must_belong_to_its_verdict() -> None:
    with pytest.raises(ValidationError):
        JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE, nuance=JudgmentNuance.FOR_LIFE)


def test_outcome_without_nuance_is_valid() -> None:
    outcome = JudgmentOutcome(verdict=JudgmentVerdict.RELEASE)
    assert outcome.nuance is None


def test_every_verdict_has_four_nuances() -> None:
    assert {verdict: len(items) for verdict, items in NUANCES_BY_VERDICT.items()} == {
        verdict: 4 for verdict in JudgmentVerdict
    }


def test_catalog_covers_all_sixteen_nuances_once() -> None:
    flattened = [item for items in NUANCES_BY_VERDICT.values() for item in items]
    assert sorted(flattened) == sorted(JudgmentNuance)
    assert len(flattened) == 16


def test_scene_package_round_trips_a_judgment_spec_and_default() -> None:
    package = _package(_spec())
    restored = ScenePackage.model_validate_json(package.model_dump_json())
    assert restored.default_outcome == JudgmentOutcome(verdict=JudgmentVerdict.IMPRISON)
    assert restored.allowed_outcomes[0].kind == "judgment"


def test_default_outcome_is_valid_for_its_package() -> None:
    assert validate_package(_package(_spec())) == []


def test_validation_rejects_a_verdict_the_package_does_not_offer() -> None:
    spec = JudgmentSpec(
        subject_kind=JudgmentSubjectKind.CAPTIVE,
        options=[
            JudgmentOption(verdict=JudgmentVerdict.IMPRISON, nuances=[]),
        ],
    )
    reasons = validate_outcome_against_package(
        _package(spec), JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE)
    )
    assert reasons == ["verdict 'execute' is not offered in this scene"]


def test_validation_rejects_a_nuance_the_package_does_not_offer() -> None:
    spec = JudgmentSpec(
        subject_kind=JudgmentSubjectKind.GOVERNOR,
        options=[
            JudgmentOption(
                verdict=JudgmentVerdict.RELEASE,
                nuances=[JudgmentNuance.WITH_WARNING],
            ),
        ],
    )
    reasons = validate_outcome_against_package(
        _package(spec),
        JudgmentOutcome(
            verdict=JudgmentVerdict.RELEASE, nuance=JudgmentNuance.WITH_FINE
        ),
    )
    assert reasons == ["nuance 'with_fine' is not offered in this scene"]


def test_tuning_is_off_by_default_with_six_turn_cooldown_and_sentence() -> None:
    tuning = JudgmentTuning()
    assert tuning.is_enabled is False
    assert tuning.cooldown_turns == 6
    assert tuning.sentence_turns == 6
    assert Tuning().judgments == tuning


def test_participant_stance_is_optional_and_decision_carries_a_nuance() -> None:
    participant = Participant(
        participant_id="veyra",
        kind=ParticipantKind.OFFICER,
        name="Veyra",
        stance=AdvisorStance.MERCY,
    )
    assert participant.stance is AdvisorStance.MERCY
    assert (
        Participant(
            participant_id="brannoch", kind=ParticipantKind.OFFICER, name="Brannoch"
        ).stance
        is None
    )
    decision = SceneDecision(
        action="choose_option", option_id="execute", nuance_id="publicly"
    )
    assert decision.nuance_id == "publicly"
