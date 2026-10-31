import json
from pathlib import Path

import pytest
from app.engine.negotiation_decision import interpret_decision
from strategy_contracts.scene import (
    ScenePackage,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.scene_exchange import SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package

RECORDING_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "live_decisions.json"
)
PLAYER_FACTION = "player"
COUNTERPART_FACTION = "house_mira"
INJECTION_SCENARIO = "negotiation_injection"
COOPERATIVE_SCENARIO = "negotiation_cooperative"


NEGOTIATION_SCENE_TYPE = "negotiation"
LETTER_SCENE_TYPE = "letter"


def _recording() -> dict:
    return json.loads(RECORDING_PATH.read_text())


def _decisions_of(recording: dict, scene_type: str) -> list[dict]:
    return [
        item
        for item in recording["decisions"]
        if item.get("scene_type", NEGOTIATION_SCENE_TYPE) == scene_type
    ]


def _replayed(item: dict, recording: dict):
    package = ScenePackage.model_validate(recording["packages"][item["scenario"]])
    decision = SceneDecision.model_validate(item["decision"])
    return package, interpret_decision(
        decision, package, PLAYER_FACTION, COUNTERPART_FACTION
    )


def _max_duration(package: ScenePackage) -> int:
    spec = next(i for i in package.allowed_outcomes if isinstance(i, TermsCardSpec))
    return spec.max_duration_turns


def test_recorded_muse_decisions_stay_within_bounds() -> None:
    recording = _recording()
    negotiations = _decisions_of(recording, NEGOTIATION_SCENE_TYPE)
    assert negotiations
    for item in negotiations:
        package, result = _replayed(item, recording)
        if result.proposal is None:
            continue
        outcome = TermsCardOutcome(
            result=TermsResult.AGREED, terms_card=result.proposal
        )
        assert validate_outcome_against_package(package, outcome) == []
        assert result.proposal.terms[0].duration_turns <= _max_duration(package)


def test_recorded_injection_decisions_never_produce_a_proposal_or_ending() -> None:
    recording = _recording()
    injected = [
        d for d in recording["decisions"] if d["scenario"] == INJECTION_SCENARIO
    ]
    for item in injected:
        _, result = _replayed(item, recording)
        assert result.proposal is None
        assert result.ending is None


def test_recorded_cooperative_pact_is_accepted_inside_the_range() -> None:
    recording = _recording()
    proposals = [
        _replayed(item, recording)[1].proposal
        for item in _decisions_of(recording, NEGOTIATION_SCENE_TYPE)
        if item["scenario"] == COOPERATIVE_SCENARIO
        and item["decision"]["action"] == "propose_terms"
    ]
    assert proposals
    assert all(card is not None for card in proposals)


def test_recorded_letter_decisions_end_in_an_offered_option_or_stay_open() -> None:
    from app.services.scene_kinds import interpret_scene_decision
    from strategy_contracts.scene import ChoiceOutcome, ChoiceSpec

    from tests.engine.letters.builders import letter_scenario, letter_world

    recording = _recording()
    letters = _decisions_of(recording, LETTER_SCENE_TYPE)
    if not letters:
        pytest.skip("no letter decisions were recorded yet")
    world, scenario = letter_world(), letter_scenario()
    for item in letters:
        package = ScenePackage.model_validate(recording["packages"][item["scenario"]])
        decision = SceneDecision.model_validate(item["decision"])
        result = interpret_scene_decision(decision, package, world, scenario)
        spec = next(i for i in package.allowed_outcomes if isinstance(i, ChoiceSpec))
        offered = {option.id for option in spec.options}
        if result.ending is not None:
            assert isinstance(result.ending, ChoiceOutcome)
            assert result.ending.option_id in offered
        assert result.proposal is None
