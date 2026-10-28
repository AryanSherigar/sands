from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.internal import events as internal_events
from app.engine.internal.queued_responses import apply_queued_responses
from app.engine.internal.rebels import end_crushed_uprisings, raise_rebel_armies
from app.engine.internal.uprising_lifecycle import (
    advance_uprisings,
    choose_archetype,
    penalty_for_stage,
)
from app.engine.outrage.effects import mobilization_exhaustion
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.pressure.effects import pressure_stability_loss, pressure_unrest
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_internal import (
    STARTING_STAGE,
    UprisingState,
    is_rebel_faction,
    uprising_for_region,
)
from app.models.world_state import UPRISING_LIFECYCLE_RULESET, WorldState
from strategy_contracts.scenario import InternalTuning, StrategyScenario


class InternalPhase:
    name = PhaseName.INTERNAL

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        if not world.internal_ruleset:
            return PhaseResult(world)
        events: list[EventLogEntry] = []
        tuning = context.scenario.tuning.internal
        is_lifecycle = world.internal_ruleset >= UPRISING_LIFECYCLE_RULESET
        events.extend(apply_queued_responses(world, tuning))
        if is_lifecycle:
            events.extend(end_crushed_uprisings(world, tuning))
        for faction_id in sorted(world.factions):
            if is_rebel_faction(faction_id):
                continue
            events.extend(_apply_faction_pressure(world, context.scenario, faction_id))
            events.extend(
                _apply_pressure_stability(world, context.scenario, faction_id)
            )
        events.extend(_apply_regional_unrest(world, context.scenario))
        if is_lifecycle:
            events.extend(advance_uprisings(world, tuning))
        events.extend(_start_uprisings(world, context, tuning))
        if is_lifecycle:
            events.extend(raise_rebel_armies(world, tuning))
        world.battle_losses = {}
        return PhaseResult(world, events)


def _active_war_count(world: WorldState, faction_id: str) -> int:
    return sum(
        faction_id in {war.attacker_id, war.defender_id, *war.participant_ids}
        for war in world.wars
    )


def _loss_units(world: WorldState, faction_id: str, tuning: InternalTuning) -> int:
    return world.battle_losses.get(faction_id, 0) // tuning.battle_loss_unit


def _apply_faction_pressure(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[EventLogEntry]:
    tuning = scenario.tuning.internal
    faction = world.factions[faction_id]
    wars = _active_war_count(world, faction_id)
    losses = world.battle_losses.get(faction_id, 0)
    units = _loss_units(world, faction_id, tuning)
    exhaustion_before, stability_before = faction.war_exhaustion, faction.stability
    faction.war_exhaustion = _next_exhaustion(
        faction.war_exhaustion, wars, units, tuning
    )
    faction.war_exhaustion = clamp(
        faction.war_exhaustion + mobilization_exhaustion(world, scenario, faction_id),
        0,
        PERCENT,
    )
    faction.stability = _next_stability(faction.stability, wars, units, tuning)
    if (exhaustion_before, stability_before) == (
        faction.war_exhaustion,
        faction.stability,
    ):
        return []
    return [
        internal_events.pressure_changed(
            faction_id,
            exhaustion_before,
            faction.war_exhaustion,
            stability_before,
            faction.stability,
            wars,
            losses,
        )
    ]


def _next_exhaustion(
    current: int, wars: int, units: int, tuning: InternalTuning
) -> int:
    if not wars:
        return clamp(current - tuning.peace_exhaustion_recovery, 0, PERCENT)
    increase = wars * tuning.war_exhaustion_per_active_war
    return clamp(
        current + increase + units * tuning.war_exhaustion_per_loss_unit, 0, PERCENT
    )


def _next_stability(current: int, wars: int, units: int, tuning: InternalTuning) -> int:
    if not wars:
        return clamp(current + tuning.peace_stability_recovery, 0, PERCENT)
    decrease = wars * tuning.stability_loss_per_active_war
    return clamp(
        current - decrease - units * tuning.stability_loss_per_loss_unit, 0, PERCENT
    )


def _apply_pressure_stability(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[EventLogEntry]:
    loss = pressure_stability_loss(world, scenario, faction_id)
    faction = world.factions[faction_id]
    if not loss or not faction.stability:
        return []
    before = faction.stability
    faction.stability = clamp(before - loss, 0, PERCENT)
    return [
        diplomacy_event(
            "pressure_stability_lost",
            [faction_id],
            {"loss": before - faction.stability},
            phase=PhaseName.INTERNAL,
        )
    ]


def _apply_regional_unrest(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    tuning = scenario.tuning.internal
    for region_id, region in sorted(world.regions.items()):
        if region.owner_id is None or region.occupation is not None:
            continue
        pressure = _regional_pressure(world, region.owner_id, tuning)
        pressure += pressure_unrest(world, scenario, region.owner_id)
        pressure += _grudge_pressure(world, region_id, tuning)
        if not pressure:
            continue
        before = region.unrest
        region.unrest = clamp(before + pressure, 0, PERCENT)
        if before != region.unrest:
            events.append(
                internal_events.regional_unrest_changed(
                    region.owner_id, region_id, before, region.unrest, pressure
                )
            )
    return events


def _regional_pressure(
    world: WorldState, faction_id: str, tuning: InternalTuning
) -> int:
    faction = world.factions[faction_id]
    war_pressure = _active_war_count(world, faction_id) * tuning.unrest_per_active_war
    stability_pressure = (
        max(0, 50 - faction.stability) // tuning.low_stability_unrest_divisor
    )
    return war_pressure + stability_pressure


def _start_uprisings(
    world: WorldState, context: PhaseContext, tuning: InternalTuning
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for region_id, region in sorted(world.regions.items()):
        if not _can_revolt(world, region_id, region.owner_id, region.unrest, tuning):
            continue
        chance = _revolt_chance(region.unrest, tuning)
        if context.rng.fork("revolt", region_id).roll(PERCENT) >= chance:
            continue
        uprising = _new_uprising(
            world, region_id, region.owner_id, region.unrest, tuning
        )
        world.uprisings.append(uprising)
        events.append(
            internal_events.uprising_started(
                uprising.id, uprising.faction_id, region_id, region.unrest, chance
            )
        )
    return events


def _can_revolt(
    world: WorldState,
    region_id: str,
    faction_id: str | None,
    unrest: int,
    tuning: InternalTuning,
) -> bool:
    cooldown = world.uprising_cooldowns.get(region_id, -tuning.uprising_cooldown_turns)
    return (
        faction_id is not None
        and unrest >= tuning.revolt_unrest_threshold
        and uprising_for_region(world.uprisings, region_id) is None
        and world.clock.turn >= cooldown + tuning.uprising_cooldown_turns
    )


def _revolt_chance(unrest: int, tuning: InternalTuning) -> int:
    excess = unrest - tuning.revolt_unrest_threshold
    return min(
        PERCENT,
        tuning.revolt_base_chance_percent + excess * tuning.revolt_chance_per_unrest,
    )


def _new_uprising(
    world: WorldState,
    region_id: str,
    faction_id: str,
    unrest: int,
    tuning: InternalTuning,
) -> UprisingState:
    if world.internal_ruleset < UPRISING_LIFECYCLE_RULESET:
        return _legacy_uprising(world, region_id, faction_id, unrest, tuning)
    archetype = choose_archetype(world, faction_id, unrest, tuning)
    stage = STARTING_STAGE[archetype]
    step = tuning.uprising_stage_penalty_step_percent
    return UprisingState(
        id=f"uprising_{region_id}_{world.clock.turn}",
        region_id=region_id,
        faction_id=faction_id,
        started_turn=world.clock.turn,
        trigger_unrest=unrest,
        income_penalty_percent=penalty_for_stage(
            tuning.uprising_income_penalty_percent, stage, step
        ),
        manpower_penalty_percent=penalty_for_stage(
            tuning.uprising_manpower_penalty_percent, stage, step
        ),
        supply_penalty_percent=penalty_for_stage(
            tuning.uprising_supply_penalty_percent, stage, step
        ),
        archetype=archetype,
        stage=stage,
    )


def _grudge_pressure(world: WorldState, region_id: str, tuning: InternalTuning) -> int:
    expires = world.region_grudges.get(region_id)
    if expires is None or world.clock.turn >= expires:
        return 0
    return tuning.restore_order_grudge_unrest


def _legacy_uprising(
    world: WorldState,
    region_id: str,
    faction_id: str,
    unrest: int,
    tuning: InternalTuning,
) -> UprisingState:
    return UprisingState(
        id=f"uprising_{region_id}_{world.clock.turn}",
        region_id=region_id,
        faction_id=faction_id,
        started_turn=world.clock.turn,
        trigger_unrest=unrest,
        income_penalty_percent=tuning.uprising_income_penalty_percent,
        manpower_penalty_percent=tuning.uprising_manpower_penalty_percent,
        supply_penalty_percent=tuning.uprising_supply_penalty_percent,
    )
