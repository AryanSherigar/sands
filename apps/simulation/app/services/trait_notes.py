from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import BUILTIN_TRAITS


def trait_notes(trait_ids: list[str], scenario: StrategyScenario) -> list[str]:
    definitions = {trait.id: trait for trait in BUILTIN_TRAITS}
    definitions |= {trait.id: trait for trait in scenario.custom_traits}
    notes = []
    for trait_id in trait_ids:
        trait = definitions.get(trait_id)
        if trait is not None and trait.description:
            notes.append(f"{trait.name}: {trait.description}")
    return notes
