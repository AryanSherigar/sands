from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import BUILTIN_STANCES, StanceDefinition


def resolve_stance_menu(
    scenario: StrategyScenario, faction_id: FactionId
) -> list[StanceDefinition]:
    available = {stance.id: stance for stance in BUILTIN_STANCES}
    available |= {stance.id: stance for stance in scenario.custom_stances}
    allowed = _allowed_ids(scenario, faction_id)
    ids = sorted(available if allowed is None else allowed & available.keys())
    return [available[stance_id] for stance_id in ids]


def _allowed_ids(scenario: StrategyScenario, faction_id: FactionId) -> set[str] | None:
    for faction in scenario.factions:
        if faction.id == faction_id and faction.stance_ids is not None:
            return set(faction.stance_ids)
    return None
