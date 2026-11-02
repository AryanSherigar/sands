from app.engine.diplomacy.reputation import shift_standing
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_state import CAPTIVITY_RULESET, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PERCENT, PeaceTuning
from strategy_contracts.scenario import StrategyScenario


def is_captivity_active(world: WorldState) -> bool:
    return world.peace_ruleset >= CAPTIVITY_RULESET


def captive_points(
    world: WorldState, prisoner: PrisonerState, tuning: PeaceTuning
) -> int:
    if prisoner.kind == PrisonerKind.CHARACTER:
        leader_id = world.factions[prisoner.origin_faction_id].leader_id
        if prisoner.character_id == leader_id:
            return tuning.captive_ruler_points
        return tuning.mercy_character_points
    return max(1, prisoner.troop_count // tuning.mercy_troops_per_point)


def _stamp_new_captives(world: WorldState) -> None:
    for prisoner in world.prisoners:
        if prisoner.held_since_turn is None:
            prisoner.held_since_turn = world.clock.turn


def _weighted_strain(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> int:
    since = (
        world.clock.turn
        if prisoner.held_since_turn is None
        else prisoner.held_since_turn
    )
    held_turns = world.clock.turn - since
    rate = tuning.captive_drain_base_percent + (
        tuning.captive_drain_growth_percent * held_turns
    )
    return captive_points(world, prisoner, tuning) * rate


def captive_drain(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    tuning = scenario.tuning.peace
    strain = sum(
        _weighted_strain(world, tuning, prisoner)
        for prisoner in world.prisoners
        if prisoner.origin_faction_id == faction_id
    )
    return min(tuning.captive_drain_cap, strain // PERCENT)


def captive_acceptance_shift(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if not is_captivity_active(world):
        return 0
    drain = captive_drain(world, scenario, faction_id)
    return drain * scenario.tuning.peace.captive_talks_weight


def prune_mercies(world: WorldState, scenario: StrategyScenario) -> None:
    duration = scenario.tuning.peace.mercy_duration_turns
    world.pressure.mercies = [
        record
        for record in world.pressure.mercies
        if world.clock.turn - record.turn < duration
    ]


def tick_captivity(world: WorldState, scenario: StrategyScenario) -> None:
    if not is_captivity_active(world):
        return
    _stamp_new_captives(world)
    prune_mercies(world, scenario)
    for faction_id in sorted({item.origin_faction_id for item in world.prisoners}):
        drain = captive_drain(world, scenario, faction_id)
        shift_standing(world.factions[faction_id], 0, -drain)


def rally_after_execution(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> None:
    if not is_captivity_active(world):
        return
    origin_id = prisoner.origin_faction_id
    shift_standing(world.factions[origin_id], 0, tuning.martyr_stability_rally)
    for army in world.armies.values():
        if army.owner_id == origin_id:
            army.morale = min(PERCENT, army.morale + tuning.martyr_morale_rally)
