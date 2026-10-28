from app.engine.battles.morale import weighted_attribute
from app.engine.battles.state import PERCENT
from app.exceptions.base import SimulationServiceError
from app.models.world_battle import (
    BattleContingent,
    BattleSide,
    BattleState,
    StandingPlan,
)
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, SupplyState, Tactic, Weather
from strategy_contracts.enums import Terrain, TroopType


def validate_tactic(
    world: WorldState,
    battle: BattleState,
    contingent: BattleContingent,
    plan: StandingPlan,
    tuning: BattleTuning,
) -> None:
    """Validate physical flank requirements before a caller reserves command cost."""
    if plan.tactic == Tactic.HOLD_HIGH_GROUND:
        _require_high_ground(battle, contingent)
        return
    if plan.tactic == Tactic.FOREST_FLANK:
        _require_forest_flank(world, battle, contingent, tuning)
        return
    if plan.tactic != Tactic.FLANK:
        return
    _require_flank(world, battle, contingent, tuning)


def _require_high_ground(battle: BattleState, contingent: BattleContingent) -> None:
    if contingent.side != BattleSide.DEFENDER or battle.terrain not in (
        Terrain.HILLS,
        Terrain.MOUNTAIN,
    ):
        raise SimulationServiceError(
            "high ground is unavailable", code="unsupported_tactic"
        )


def _require_forest_flank(
    world: WorldState,
    battle: BattleState,
    contingent: BattleContingent,
    tuning: BattleTuning,
) -> None:
    if battle.terrain != Terrain.FOREST:
        raise SimulationServiceError(
            "forest flank is unavailable", code="unsupported_tactic"
        )
    _require_flank(world, battle, contingent, tuning, allow_forest=True)


def _require_flank(
    world: WorldState,
    battle: BattleState,
    contingent: BattleContingent,
    tuning: BattleTuning,
    *,
    allow_forest: bool = False,
) -> None:
    armies = [
        world.armies[army_id]
        for army_id in contingent.army_ids
        if army_id in world.armies
    ]
    total = sum(sum(army.troops.values()) for army in armies)
    cavalry = sum(army.troops.get(TroopType.CAVALRY, 0) for army in armies)
    if (
        (not allow_forest and not tuning.terrain_flank_allowed[battle.terrain])
        or not total
        or cavalry * PERCENT < total * tuning.flank_min_cavalry_percent
    ):
        raise SimulationServiceError(
            "flank requirements are unavailable", code="unsupported_tactic"
        )


def _troop_attack(
    count: int,
    troop_type: TroopType,
    battle: BattleState,
    contingent: BattleContingent,
    tuning: BattleTuning,
) -> int:
    pressure = count * tuning.troop_attack[troop_type]
    if troop_type == TroopType.CAVALRY:
        return (
            pressure * tuning.cavalry_terrain_attack_percent[battle.terrain] // PERCENT
        )
    if troop_type == TroopType.ARCHERS_SIEGE and contingent.side == BattleSide.DEFENDER:
        return (
            pressure * tuning.defending_archer_attack_percent[battle.terrain] // PERCENT
        )
    return pressure


def attack_pressure(
    world: WorldState,
    battle: BattleState,
    contingent: BattleContingent,
    tuning: BattleTuning,
) -> int:
    pressure = sum(
        _troop_attack(count, troop_type, battle, contingent, tuning)
        for deployment in contingent.deployments.values()
        for troop_type, count in deployment.active.items()
    )
    factor = max(
        tuning.morale_factor_floor_percent,
        tuning.morale_factor_base_percent
        + weighted_attribute(world, contingent, "morale")
        - weighted_attribute(world, contingent, "fatigue")
        // tuning.fatigue_morale_divisor,
    )
    factors = (
        tuning.formation_attack_percent[contingent.plan.formation],
        tuning.tactic_attack_percent[contingent.plan.tactic],
        tuning.weather_attack_percent[battle.weather or Weather.CLEAR],
        tuning.supply_attack_percent[contingent.supply or SupplyState.SUPPLIED],
        factor,
    )
    for percent in factors:
        pressure = pressure * percent // PERCENT
    return pressure


def average_protection(
    battle: BattleState, contingent: BattleContingent, tuning: BattleTuning
) -> int:
    engaged = sum(
        sum(deployment.active.values())
        for deployment in contingent.deployments.values()
    )
    protection = max(
        1,
        sum(
            count * tuning.troop_protection[troop_type]
            for deployment in contingent.deployments.values()
            for troop_type, count in deployment.active.items()
        )
        // max(1, engaged),
    )
    factors = (
        tuning.formation_protection_percent[contingent.plan.formation],
        tuning.tactic_protection_percent[contingent.plan.tactic],
        tuning.weather_protection_percent[battle.weather or Weather.CLEAR],
    )
    for percent in factors:
        protection = max(1, protection * percent // PERCENT)
    return protection
