from app.engine.pressure.captivity import captive_points, is_captivity_active
from app.engine.pressure.wars import find_war
from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import PrisonerState
from app.models.world_pressure import MercyRecord
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

RECEPTIVE_AXES = (TraitAxis.HONOR, TraitAxis.TRUST)
WARY_AXES = (
    TraitAxis.CRUELTY,
    TraitAxis.GREED,
    TraitAxis.CUNNING,
    TraitAxis.PRIDE,
)


def _trait_percent(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    tuning = scenario.tuning.peace
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if leader is None:
        return PERCENT
    totals = axis_totals(leader, scenario)
    receptive = sum(totals.get(axis, 0) for axis in RECEPTIVE_AXES)
    wary = sum(totals.get(axis, 0) for axis in WARY_AXES)
    percent = PERCENT + tuning.mercy_trait_percent_step * (receptive - wary)
    return min(tuning.mercy_max_percent, max(tuning.mercy_min_percent, percent))


def _average_morale(world: WorldState, faction_id: FactionId) -> int:
    morales = [a.morale for a in world.armies.values() if a.owner_id == faction_id]
    return sum(morales) // len(morales) if morales else 0


def _condition_percent(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    strain = (
        2 * PERCENT
        - world.factions[faction_id].stability
        - _average_morale(world, faction_id)
    ) // 2
    return scenario.tuning.peace.mercy_condition_base_percent + strain


def mercy_amount(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> int:
    freed_id = prisoner.origin_faction_id
    points = captive_points(world, prisoner, scenario.tuning.peace)
    traits = _trait_percent(world, scenario, freed_id)
    condition = _condition_percent(world, scenario, freed_id)
    return points * traits * condition // (PERCENT * PERCENT)


def record_mercy(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> None:
    war = find_war(world, prisoner.held_by_id, prisoner.origin_faction_id)
    if war is None or not world.pressure_ruleset or not is_captivity_active(world):
        return
    world.pressure.mercies.append(
        MercyRecord(
            war_id=war.id,
            faction_id=prisoner.origin_faction_id,
            amount=mercy_amount(world, scenario, prisoner),
            turn=world.clock.turn,
        )
    )


def mercy_total(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    tuning = scenario.tuning.peace
    active_war_ids = {war.id for war in world.wars}
    total = 0
    for record in world.pressure.mercies:
        if record.faction_id != faction_id or record.war_id not in active_war_ids:
            continue
        remaining = tuning.mercy_duration_turns - (world.clock.turn - record.turn)
        total += record.amount * max(0, remaining) // tuning.mercy_duration_turns
    return min(tuning.mercy_will_cap, max(-tuning.mercy_will_cap, total))
