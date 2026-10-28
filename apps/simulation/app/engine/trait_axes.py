from collections import Counter

from app.models.world_character import LeaderState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import BUILTIN_TRAITS, TraitAxis


def axis_totals(leader: LeaderState, scenario: StrategyScenario) -> Counter[TraitAxis]:
    definitions = {trait.id: trait for trait in BUILTIN_TRAITS}
    definitions |= {trait.id: trait for trait in scenario.custom_traits}
    totals: Counter[TraitAxis] = Counter()
    for trait_id in leader.trait_ids:
        trait = definitions.get(trait_id)
        if trait is not None:
            totals.update(trait.effects)
    return totals
