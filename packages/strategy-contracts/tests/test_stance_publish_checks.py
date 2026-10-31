from collections.abc import Callable

from strategy_contracts.examples import load_three_crowns
from strategy_contracts.publish_checks import IssueCode, check_publishable
from strategy_contracts.scenario import StrategyScenario

Document = dict[str, object]

STANCE_CODES = {
    IssueCode.STANCE_ID_COLLISION,
    IssueCode.UNKNOWN_STANCE_REFERENCE,
    IssueCode.EMPTY_STANCE_MENU,
}


def _edited(mutate: Callable[[Document], None]) -> StrategyScenario:
    document = load_three_crowns().model_dump(mode="json")
    mutate(document)
    return StrategyScenario.model_validate(document)


def _blocking_codes(scenario: StrategyScenario) -> set[IssueCode]:
    return {issue.code for issue in check_publishable(scenario).blocking}


def _custom_stance(stance_id: str) -> dict[str, object]:
    return {"id": stance_id, "name": "Custom", "shifts": {"attack": 1}}


def test_custom_stance_colliding_with_builtin_id_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["custom_stances"] = [_custom_stance("turtle")]

    assert IssueCode.STANCE_ID_COLLISION in _blocking_codes(_edited(mutate))


def test_duplicate_custom_stance_ids_are_blocking() -> None:
    def mutate(document: Document) -> None:
        document["custom_stances"] = [
            _custom_stance("reclaim"),
            _custom_stance("reclaim"),
        ]

    assert IssueCode.STANCE_ID_COLLISION in _blocking_codes(_edited(mutate))


def test_faction_referencing_unknown_stance_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["factions"][0]["stance_ids"] = ["nonexistent"]

    report = check_publishable(_edited(mutate))
    unknown = [
        issue
        for issue in report.blocking
        if issue.code is IssueCode.UNKNOWN_STANCE_REFERENCE
    ]
    assert unknown
    assert unknown[0].path == "factions[0].stance_ids[0]"


def test_faction_with_empty_stance_ids_list_is_blocking() -> None:
    def mutate(document: Document) -> None:
        document["factions"][0]["stance_ids"] = []

    assert IssueCode.EMPTY_STANCE_MENU in _blocking_codes(_edited(mutate))


def test_valid_custom_stance_and_faction_menu_raise_no_stance_issue() -> None:
    def mutate(document: Document) -> None:
        document["custom_stances"] = [_custom_stance("reclaim")]
        document["factions"][0]["stance_ids"] = ["reclaim", "turtle"]

    assert not _blocking_codes(_edited(mutate)) & STANCE_CODES


def test_scenario_without_stances_still_publishes() -> None:
    assert not _blocking_codes(load_three_crowns()) & STANCE_CODES
