from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.internal.uprising_lifecycle import apply_stage, penalty_for_stage
from app.engine.revolt.constants import (
    COVENANT_BROKEN,
    REGION_SUBJECT_INDEX,
    RESTORE_ORDER_KEY,
)
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_internal import (
    STAGE_ORDER,
    UprisingArchetype,
    UprisingStage,
    UprisingState,
)
from app.models.world_state import WorldState
from strategy_contracts.enums import TaxRate
from strategy_contracts.revolt import CovenantKind, CovenantState, CovenantStatus
from strategy_contracts.scenario import StrategyScenario

TAX_RATES_AGAINST_RELIEF = frozenset({TaxRate.HIGH, TaxRate.NORMAL})
LAST_STAGE_INDEX = len(STAGE_ORDER) - 1


def _is_crackdown(covenant: CovenantState, event: EventLogEntry) -> bool:
    ids = event.cause.subject_ids
    return (
        event.kind == "uprising_resolved"
        and event.cause.summary_key == RESTORE_ORDER_KEY
        and len(ids) > REGION_SUBJECT_INDEX
        and ids[REGION_SUBJECT_INDEX] == covenant.region_id
    )


def _has_army_in_region(world: WorldState, covenant: CovenantState) -> bool:
    return any(
        army.owner_id == covenant.faction_id and army.location_id == covenant.region_id
        for army in world.armies.values()
    )


def is_covenant_broken(
    world: WorldState, covenant: CovenantState, events: list[EventLogEntry]
) -> bool:
    if covenant.covenant is CovenantKind.TAX_RELIEF:
        return world.factions[covenant.faction_id].tax_rate in TAX_RATES_AGAINST_RELIEF
    if covenant.covenant is CovenantKind.GARRISON_OUT:
        return _has_army_in_region(world, covenant)
    if covenant.covenant is CovenantKind.AMNESTY:
        return any(_is_crackdown(covenant, event) for event in events)
    return False


def _reignite(
    world: WorldState, covenant: CovenantState, scenario: StrategyScenario
) -> None:
    target = UprisingStage(covenant.relapse_stage.value)
    step = scenario.tuning.internal.uprising_stage_penalty_step_percent
    existing = next(
        (item for item in world.uprisings if item.region_id == covenant.region_id),
        None,
    )
    if existing is None:
        world.uprisings.append(_relapse_uprising(world, covenant, target, scenario))
        return
    next_index = min(STAGE_ORDER.index(existing.stage) + 1, LAST_STAGE_INDEX)
    stage = STAGE_ORDER[max(next_index, STAGE_ORDER.index(target))]
    apply_stage(existing, stage, step)


def _relapse_uprising(
    world: WorldState,
    covenant: CovenantState,
    stage: UprisingStage,
    scenario: StrategyScenario,
) -> UprisingState:
    internal = scenario.tuning.internal
    step = internal.uprising_stage_penalty_step_percent
    return UprisingState(
        id=f"uprising_{covenant.region_id}_{world.clock.turn}",
        region_id=covenant.region_id,
        faction_id=covenant.faction_id,
        started_turn=world.clock.turn,
        trigger_unrest=world.regions[covenant.region_id].unrest,
        income_penalty_percent=penalty_for_stage(
            internal.uprising_income_penalty_percent, stage, step
        ),
        manpower_penalty_percent=penalty_for_stage(
            internal.uprising_manpower_penalty_percent, stage, step
        ),
        supply_penalty_percent=penalty_for_stage(
            internal.uprising_supply_penalty_percent, stage, step
        ),
        archetype=UprisingArchetype.REBELLION,
        stage=stage,
    )


def _break(
    world: WorldState,
    covenant: CovenantState,
    scenario: StrategyScenario,
    phase: PhaseName,
) -> EventLogEntry:
    tuning = scenario.tuning.revolt_talk
    covenant.status = CovenantStatus.BREACHED
    region = world.regions[covenant.region_id]
    faction = world.factions[covenant.faction_id]
    region.unrest = clamp(region.unrest + tuning.breach_unrest, 0, PERCENT)
    faction.reputation = clamp(
        faction.reputation - tuning.breach_reputation_cost, -PERCENT, PERCENT
    )
    world.revolt_lockouts[covenant.region_id] = (
        world.clock.turn + tuning.breach_lockout_turns
    )
    _reignite(world, covenant, scenario)
    return diplomacy_event(
        COVENANT_BROKEN,
        [covenant.faction_id, covenant.region_id, covenant.covenant.value],
        phase=phase,
        is_major=True,
    )


def scan_covenants(
    world: WorldState,
    scenario: StrategyScenario,
    phase_events: list[EventLogEntry],
    phase: PhaseName,
) -> list[EventLogEntry]:
    """Breach active covenants the world now contradicts; settle those past their term."""
    broken: list[EventLogEntry] = []
    for covenant in world.covenants:
        if covenant.status is not CovenantStatus.ACTIVE:
            continue
        if world.regions[covenant.region_id].owner_id != covenant.faction_id:
            covenant.status = CovenantStatus.EXPIRED
        elif is_covenant_broken(world, covenant, phase_events):
            broken.append(_break(world, covenant, scenario, phase))
        elif covenant.end_turn < world.clock.turn:
            covenant.status = CovenantStatus.FULFILLED
    return broken
