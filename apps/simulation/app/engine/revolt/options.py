from app.models.world_events import PendingRevoltTalk
from app.models.world_state import WorldState
from strategy_contracts.revolt import (
    REVOLT_TALK_OPTIONS,
    CovenantKind,
    RevoltTalkOption,
)
from strategy_contracts.scenario import StrategyScenario


def _relief_cost(kind: CovenantKind, scenario: StrategyScenario) -> int:
    tuning = scenario.tuning.revolt_talk
    if kind is CovenantKind.RELIEF_SMALL:
        return tuning.relief_small_gold
    if kind is CovenantKind.RELIEF_LARGE:
        return tuning.relief_large_gold
    return 0


def option_cost(option: RevoltTalkOption, scenario: StrategyScenario) -> int:
    return sum(_relief_cost(kind, scenario) for kind in option.covenants)


def _has_own_army_in_region(world: WorldState, pending: PendingRevoltTalk) -> bool:
    return any(
        army.owner_id == pending.faction_id and army.location_id == pending.region_id
        for army in world.armies.values()
    )


def is_option_available(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingRevoltTalk,
    option: RevoltTalkOption,
) -> bool:
    if option_cost(option, scenario) > world.factions[pending.faction_id].treasury:
        return False
    is_garrison_covenant = CovenantKind.GARRISON_OUT in option.covenants
    return not (is_garrison_covenant and _has_own_army_in_region(world, pending))


def available_options(
    world: WorldState, scenario: StrategyScenario, pending: PendingRevoltTalk
) -> list[RevoltTalkOption]:
    return [
        option
        for option in REVOLT_TALK_OPTIONS
        if is_option_available(world, scenario, pending, option)
    ]
