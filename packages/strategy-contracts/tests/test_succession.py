from collections.abc import Callable

import pytest
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.pressure import RumorTopic, ShockKind
from strategy_contracts.publish_checks import IssueCode, check_publishable
from strategy_contracts.scenario import LeaderSetup, StrategyScenario, Tuning
from strategy_contracts.succession import HealthBand, HeirSetup, SuccessionTuning

Document = dict[str, object]


def _heir(heir_id: str = "heir_a", **overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "id": heir_id,
        "name": "Young Heir",
        "trait_ids": ["honorable", "cautious"],
        "ambition_ids": [],
        "age": 20,
    }
    document.update(overrides)
    return document


def _edited(mutate: Callable[[Document], None]) -> StrategyScenario:
    document = load_three_crowns().model_dump(mode="json")
    mutate(document)
    return StrategyScenario.model_validate(document)


def _blocking_codes(scenario: StrategyScenario) -> set[IssueCode]:
    return {issue.code for issue in check_publishable(scenario).blocking}


def _warning_codes(scenario: StrategyScenario) -> set[IssueCode]:
    return {issue.code for issue in check_publishable(scenario).warnings}


def _leader(document: Document, index: int = 0) -> dict[str, object]:
    return document["leaders"][index]


def _non_playable_leader_index(document: Document) -> int:
    playable = {
        faction["id"] for faction in document["factions"] if faction["is_playable"]
    }
    return next(
        index
        for index, leader in enumerate(document["leaders"])
        if leader["faction_id"] not in playable
    )


def test_defaults_match_spec() -> None:
    tuning = Tuning().succession

    assert tuning.ailing_age == 55
    assert tuning.failing_age == 70
    assert tuning.stress_worsens_at == 70
    assert tuning.death_per_mille == {
        HealthBand.ROBUST: 2,
        HealthBand.AILING: 25,
        HealthBand.FAILING: 120,
    }
    assert tuning.old_age_step_per_mille == 5
    assert tuning.max_death_per_mille == 500
    assert tuning.crisis_turns == 6
    assert tuning.crisis_stability_loss == 3
    assert tuning.crisis_unrest == 2
    assert tuning.crisis_acceptance_shift == 5
    assert tuning.coming_of_age == 16
    assert tuning.regent_age == 45


def test_death_table_covers_every_band() -> None:
    with pytest.raises(ValidationError):
        SuccessionTuning(death_per_mille={HealthBand.ROBUST: 1})


def test_ruler_died_shock_and_health_rumor_exist_with_a_default_amount() -> None:
    assert ShockKind.RULER_DIED in Tuning().pressure.shock_amounts
    assert RumorTopic.HEALTH.value == "health"


def test_heir_nests_one_level() -> None:
    grandchild = _heir("heir_b")
    child = _heir("heir_a", heir=grandchild)
    assert HeirSetup.model_validate(child).heir is not None
    too_deep = _heir("heir_a", heir=_heir("heir_b", heir=_heir("heir_c")))
    with pytest.raises(ValidationError):
        LeaderSetup.model_validate(
            {
                "id": "ruler",
                "name": "Ruler",
                "faction_id": "f",
                "trait_ids": ["honorable"],
                "ambition_ids": [],
                "heir": too_deep,
            }
        )


def test_example_with_no_heirs_stays_publishable_without_new_issues() -> None:
    report = check_publishable(load_three_crowns())
    assert IssueCode.HEIR_INVALID not in {issue.code for issue in report.blocking}
    assert IssueCode.AGE_IMPLAUSIBLE not in {issue.code for issue in report.warnings}


def test_publish_flags_unknown_heir_trait_as_blocking() -> None:
    def mutate(document: Document) -> None:
        index = _non_playable_leader_index(document)
        _leader(document, index)["heir"] = _heir(trait_ids=["no_such_trait"])

    assert IssueCode.HEIR_INVALID in _blocking_codes(_edited(mutate))


def test_publish_flags_heir_id_clashing_with_a_leader_as_blocking() -> None:
    def mutate(document: Document) -> None:
        index = _non_playable_leader_index(document)
        clash = _leader(document, 0)["id"]
        _leader(document, index)["heir"] = _heir(clash)

    assert IssueCode.DUPLICATE_ID in _blocking_codes(_edited(mutate))


def test_publish_warns_on_implausible_ages() -> None:
    def old_heir(document: Document) -> None:
        index = _non_playable_leader_index(document)
        _leader(document, index)["heir"] = _heir(age=81)

    def old_ruler(document: Document) -> None:
        _leader(document, 0)["age"] = 101

    assert IssueCode.AGE_IMPLAUSIBLE in _warning_codes(_edited(old_heir))
    assert IssueCode.AGE_IMPLAUSIBLE in _warning_codes(_edited(old_ruler))


def test_regent_needs_two_or_three_traits() -> None:
    with pytest.raises(ValidationError):
        SuccessionTuning(regent_trait_ids=["pragmatic"])
    with pytest.raises(ValidationError):
        SuccessionTuning(
            regent_trait_ids=["pragmatic", "cautious", "proud", "honorable"]
        )
