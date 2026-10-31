from collections.abc import Callable

from strategy_contracts.examples import load_three_crowns
from strategy_contracts.publish_checks import Issue, IssueCode, check_publishable
from strategy_contracts.scenario import StrategyScenario

Document = dict[str, object]

ASHFORD = "house_ashford"
ASHFORD_PATH = "factions[0]"


def _edited(mutate: Callable[[Document], None]) -> StrategyScenario:
    document = load_three_crowns().model_dump(mode="json")
    mutate(document)
    return StrategyScenario.model_validate(document)


def _blocking(scenario: StrategyScenario, code: IssueCode) -> list[Issue]:
    return [i for i in check_publishable(scenario).blocking if i.code == code]


def _drop_armies(document: Document) -> None:
    armies = document["starting"]["armies"]
    document["starting"]["armies"] = [a for a in armies if a["owner_id"] != ASHFORD]


def _zero_wealth(document: Document) -> None:
    for setup in document["starting"]["regions"]:
        if setup["owner_id"] == ASHFORD:
            setup["wealth"] = 0


def test_faction_without_army_is_blocking() -> None:
    issues = _blocking(_edited(_drop_armies), IssueCode.FACTION_HAS_NO_ARMY)
    assert [i.path for i in issues] == [ASHFORD_PATH]


def test_faction_with_army_passes() -> None:
    assert _blocking(load_three_crowns(), IssueCode.FACTION_HAS_NO_ARMY) == []


def test_army_with_zero_troops_does_not_count() -> None:
    def mutate(document: Document) -> None:
        for army in document["starting"]["armies"]:
            if army["owner_id"] == ASHFORD:
                army["troops"] = {"infantry": 0}

    issues = _blocking(_edited(mutate), IssueCode.FACTION_HAS_NO_ARMY)
    assert [i.path for i in issues] == [ASHFORD_PATH]


def test_faction_owning_only_zero_wealth_regions_is_blocking() -> None:
    issues = _blocking(_edited(_zero_wealth), IssueCode.FACTION_HAS_NO_ECONOMY)
    assert [i.path for i in issues] == [ASHFORD_PATH]


def test_faction_with_wealthy_region_passes() -> None:
    assert _blocking(load_three_crowns(), IssueCode.FACTION_HAS_NO_ECONOMY) == []
