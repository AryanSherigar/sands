from strategy_contracts.examples import (
    load_three_crowns,
    load_three_crowns_expanded,
)
from strategy_contracts.publish_checks import check_publishable
from strategy_contracts.scenario import StrategyScenario


def test_three_crowns_has_expected_shape() -> None:
    scenario = load_three_crowns()
    assert len(scenario.map.regions) == 6
    assert len(scenario.factions) == 3
    playable = [faction.id for faction in scenario.factions if faction.is_playable]
    assert playable == ["house_carrow"]


def test_three_crowns_round_trips() -> None:
    scenario = load_three_crowns()
    restored = StrategyScenario.model_validate_json(scenario.model_dump_json())
    assert restored == scenario


def test_mira_traits() -> None:
    leaders = {leader.id: leader for leader in load_three_crowns().leaders}
    assert leaders["mira"].trait_ids == ["cunning", "proud"]


def test_three_crowns_expanded_has_expected_shape() -> None:
    scenario = load_three_crowns_expanded()
    assert len(scenario.map.regions) == 10
    assert len(scenario.factions) == 3

    playable = [faction.id for faction in scenario.factions if faction.is_playable]
    assert playable == ["house_carrow"]

    neutral_regions = [
        setup.region_id for setup in scenario.starting.regions if setup.owner_id is None
    ]
    assert neutral_regions == ["kings_ford"]

    commander_ids = {commander.id for commander in scenario.commanders}
    assert commander_ids == {"cmd_brand", "cmd_renaud", "cmd_tormund"}

    governor_ids = {governor.id for governor in scenario.governors}
    assert governor_ids == {"gov_oswin", "gov_danica"}


def test_three_crowns_expanded_round_trips() -> None:
    scenario = load_three_crowns_expanded()
    restored = StrategyScenario.model_validate_json(scenario.model_dump_json())
    assert restored == scenario


def test_three_crowns_expanded_is_publishable() -> None:
    scenario = load_three_crowns_expanded()
    report = check_publishable(scenario)
    assert report.blocking == []
    assert report.is_publishable is True
