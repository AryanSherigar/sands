from uuid import UUID

from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.revolt.constants import COVENANT_MADE, REVOLT_TALK_HELD
from app.engine.revolt.options import option_cost
from app.models.world_events import EventLogEntry, PendingRevoltTalk, PhaseName
from app.models.world_internal import STARTING_STAGE, UprisingStage
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import TaxRate
from strategy_contracts.revolt import (
    BREACHABLE_KINDS,
    CovenantKind,
    CovenantState,
    RelapseStage,
    RevoltTalkOption,
)
from strategy_contracts.scenario import StrategyScenario


def relapse_stage_for(pending: PendingRevoltTalk) -> RelapseStage:
    started = STARTING_STAGE[pending.archetype]
    if started is UprisingStage.UNREST:
        return RelapseStage.RIOT
    return RelapseStage.ARMED


def _unrest_reduction(option: RevoltTalkOption, scenario: StrategyScenario) -> int:
    if not option.covenants:
        return scenario.tuning.internal.negotiate_unrest_reduction
    return scenario.tuning.revolt_talk.covenant_unrest_reduction * len(option.covenants)


def _sign_covenant(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingRevoltTalk,
    kind: CovenantKind,
    scene_id: UUID,
) -> EventLogEntry:
    number = next_counter(world, CounterKind.COMMITMENT)
    turns = scenario.tuning.revolt_talk.covenant_turns
    world.covenants.append(
        CovenantState(
            id=f"covenant_{number}",
            faction_id=pending.faction_id,
            region_id=pending.region_id,
            covenant=kind,
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + turns,
            relapse_stage=relapse_stage_for(pending),
            origin_scene_id=str(scene_id),
        )
    )
    return diplomacy_event(
        COVENANT_MADE,
        [pending.faction_id, pending.region_id, kind.value],
        {"duration_turns": turns},
        phase=PhaseName.DIPLOMACY,
        is_major=True,
    )


def apply_revolt_option(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingRevoltTalk,
    option: RevoltTalkOption,
    scene_id: UUID,
) -> list[EventLogEntry]:
    region = world.regions[pending.region_id]
    faction = world.factions[pending.faction_id]
    faction.treasury -= option_cost(option, scenario)
    if CovenantKind.TAX_RELIEF in option.covenants:
        faction.tax_rate = TaxRate.LOW
    reduction = _unrest_reduction(option, scenario)
    region.unrest = clamp(region.unrest - reduction, 0, PERCENT)
    events = [
        diplomacy_event(
            REVOLT_TALK_HELD,
            [pending.faction_id, pending.region_id, option.id],
            {"unrest_reduction": reduction},
            is_major=True,
        )
    ]
    for kind in option.covenants:
        if kind in BREACHABLE_KINDS:
            events.append(_sign_covenant(world, scenario, pending, kind, scene_id))
    return events
