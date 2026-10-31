from collections.abc import Callable

from strategy_contracts.conditions import (
    Comparison,
    ConditionMetric,
    ConditionOperator,
    Negation,
)
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.publish_checks import IssueCode, check_publishable
from strategy_contracts.scenario import StrategyScenario

Document = dict[str, object]


def _edited(mutate: Callable[[Document], None]) -> StrategyScenario:
    document = load_three_crowns().model_dump(mode="json")
    mutate(document)
    return StrategyScenario.model_validate(document)


def _blocking_codes(scenario: StrategyScenario) -> set[IssueCode]:
    return {issue.code for issue in check_publishable(scenario).blocking}


def _region(document: Document, region_id: str) -> dict[str, object]:
    regions = document["map"]["regions"]
    return next(region for region in regions if region["id"] == region_id)


def test_example_is_publishable_with_two_size_warnings() -> None:
    report = check_publishable(load_three_crowns())
    assert report.blocking == []
    assert report.is_publishable
    assert {issue.code for issue in report.warnings} == {
        IssueCode.FEW_FACTIONS,
        IssueCode.FEW_REGIONS,
    }


def test_empty_draft_is_reported_not_raised() -> None:
    report = check_publishable(StrategyScenario())
    assert not report.is_publishable
    assert IssueCode.NO_PLAYABLE_FACTION in {issue.code for issue in report.blocking}


def test_one_way_link_is_blocking() -> None:
    def mutate(document: Document) -> None:
        _region(document, "brennmoor")["neighbor_ids"].remove("ashford")

    assert IssueCode.MAP_ONE_WAY_LINK in _blocking_codes(_edited(mutate))


def test_isolated_region_makes_map_disconnected() -> None:
    def mutate(document: Document) -> None:
        _region(document, "ashford")["neighbor_ids"] = []
        _region(document, "brennmoor")["neighbor_ids"].remove("ashford")
        _region(document, "carrow_vale")["neighbor_ids"].remove("ashford")

    assert IssueCode.MAP_DISCONNECTED in _blocking_codes(_edited(mutate))


def test_duplicate_region_id_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["map"]["regions"].append(dict(_region(document, "ashford")))

    assert IssueCode.DUPLICATE_ID in _blocking_codes(_edited(mutate))


def test_dangling_capital_is_reported_with_path() -> None:
    def mutate(document: Document) -> None:
        document["factions"][0]["capital_region_id"] = "nowhere"

    report = check_publishable(_edited(mutate))
    dangling = [i for i in report.blocking if i.code is IssueCode.DANGLING_REFERENCE]
    assert dangling
    assert dangling[0].path.startswith("factions[")


def test_leader_without_traits_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["leaders"][0]["trait_ids"] = []

    assert IssueCode.LEADER_HAS_NO_TRAIT in _blocking_codes(_edited(mutate))


def test_disabling_default_endings_requires_custom_ones() -> None:
    def mutate(document: Document) -> None:
        document["is_using_default_endings"] = False

    codes = _blocking_codes(_edited(mutate))
    assert {IssueCode.NO_VICTORY_ENDING, IssueCode.NO_DEFEAT_ENDING} <= codes


def test_deeply_nested_condition_is_blocking() -> None:
    leaf = Comparison(
        metric=ConditionMetric.TURN, operator=ConditionOperator.GT, value=1
    )
    deep = leaf
    for _ in range(4):
        deep = Negation(condition=deep)

    def mutate(document: Document) -> None:
        document["ambitions"][0]["condition"] = deep.model_dump(mode="json")

    assert IssueCode.CONDITION_TOO_DEEP in _blocking_codes(_edited(mutate))


def test_majority_holder_is_lopsided() -> None:
    def mutate(document: Document) -> None:
        for setup in document["starting"]["regions"][:4]:
            setup["owner_id"] = "house_ashford"

    report = check_publishable(_edited(mutate))
    assert IssueCode.LOPSIDED_START in {issue.code for issue in report.warnings}


def _custom_event(**overrides: object) -> Document:
    event: Document = {
        "id": "custom_event",
        "name": "Custom",
        "subject_kind": "faction",
        "cause_key": "custom_event",
        "tiers": [
            {
                "level": 1,
                "trigger": {
                    "kind": "comparison",
                    "metric": "turn",
                    "operator": "gte",
                    "value": 1,
                },
            }
        ],
        "choices": [
            {"id": "one", "label_hint": "one", "effects": []},
            {"id": "two", "label_hint": "two", "effects": []},
        ],
        "neglect_effects": [{"kind": "stability", "amount": -1}],
    }
    return event | overrides


def test_event_effect_with_unknown_target_is_blocking() -> None:
    effects = [{"kind": "gold", "amount": -5, "target_id": "house_nowhere"}]

    def mutate(document: Document) -> None:
        document["events"] = [_custom_event(neglect_effects=effects)]

    assert IssueCode.DANGLING_REFERENCE in _blocking_codes(_edited(mutate))


def test_duplicate_custom_event_ids_are_blocking() -> None:
    def mutate(document: Document) -> None:
        document["events"] = [_custom_event(), _custom_event()]

    assert IssueCode.DUPLICATE_ID in _blocking_codes(_edited(mutate))


def test_disabling_an_unknown_builtin_event_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["disabled_builtin_event_ids"] = ["no_such_event"]

    assert IssueCode.DANGLING_REFERENCE in _blocking_codes(_edited(mutate))


def test_valid_custom_event_and_disabled_builtin_stay_publishable() -> None:
    def mutate(document: Document) -> None:
        document["events"] = [_custom_event()]
        document["disabled_builtin_event_ids"] = ["tax_grievance"]

    assert _blocking_codes(_edited(mutate)) == set()
