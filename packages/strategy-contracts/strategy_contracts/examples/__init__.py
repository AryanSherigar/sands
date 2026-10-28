from importlib.resources import files

from strategy_contracts.scenario import StrategyScenario

THREE_CROWNS_RESOURCE = "three_crowns.json"
THREE_CROWNS_EXPANDED_RESOURCE = "three_crowns_expanded.json"


def load_three_crowns() -> StrategyScenario:
    raw_json = (files(__package__) / THREE_CROWNS_RESOURCE).read_text(encoding="utf-8")
    return StrategyScenario.model_validate_json(raw_json)


def load_three_crowns_expanded() -> StrategyScenario:
    raw_json = (files(__package__) / THREE_CROWNS_EXPANDED_RESOURCE).read_text(
        encoding="utf-8"
    )
    return StrategyScenario.model_validate_json(raw_json)
