from collections.abc import Mapping
from typing import TypeVar

from app.engine.battles.state import (
    PERCENT,
    contingent_armies,
    side_contingents,
    troop_count,
)
from app.models.world_battle import (
    ArmyDeployment,
    BattleContingent,
    BattleSide,
    BattleState,
    ContingentStatus,
)
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, ReservePolicy
from strategy_contracts.enums import TroopType

AllocationKey = TypeVar("AllocationKey", bound=str | tuple[str, str])


def allocate_largest_remainder(
    total: int, weights: Mapping[AllocationKey, int]
) -> dict[AllocationKey, int]:
    """Allocate bounded integer quantities with stable lexicographic remainder ties."""
    denominator = sum(weights.values())
    total = min(total, denominator)
    if denominator == 0:
        return {key: 0 for key in sorted(weights)}
    allocated = {key: total * weights[key] // denominator for key in sorted(weights)}
    ranked = sorted(
        weights, key=lambda key: (-(total * weights[key] % denominator), key)
    )
    for key in ranked[: total - sum(allocated.values())]:
        allocated[key] += 1
    return allocated


def _initial_allocation(
    world: WorldState, battle: BattleState, side: BattleSide, tuning: BattleTuning
) -> dict[str, int]:
    contingents = side_contingents(battle, side)
    weights = {
        contingent.faction_id: troop_count(world, contingent)
        * (PERCENT - tuning.formation_reserve_percent[contingent.plan.formation])
        for contingent in contingents
    }
    soldiers = sum(troop_count(world, contingent) for contingent in contingents)
    width = tuning.frontage[battle.terrain]
    target = (
        max(
            1,
            min(soldiers, width) * sum(weights.values()) // max(1, soldiers * PERCENT),
        )
        if soldiers
        else 0
    )
    if not sum(weights.values()):
        weights = {
            contingent.faction_id: troop_count(world, contingent)
            for contingent in contingents
        }
    return allocate_largest_remainder(target, weights)


def initialize_targets(
    world: WorldState, battle: BattleState, tuning: BattleTuning
) -> None:
    """Initialize once; casualties replace vacancies without resetting standing targets."""
    for side in BattleSide:
        allocations = _initial_allocation(world, battle, side, tuning)
        contingents = side_contingents(battle, side)
        for contingent in contingents:
            contingent.desired_active = allocations[contingent.faction_id]


def _should_commit(
    world: WorldState, contingent: BattleContingent, tuning: BattleTuning
) -> bool:
    if contingent.plan.reserve_policy != ReservePolicy.REINFORCE_ON_PRESSURE:
        return False
    losses = contingent.entry_troops - troop_count(world, contingent)
    return losses * PERCENT >= contingent.entry_troops * tuning.reserve_pressure_percent


def _requests(
    world: WorldState, battle: BattleState, side: BattleSide, tuning: BattleTuning
) -> dict[str, int]:
    requests: dict[str, int] = {}
    for contingent in side_contingents(battle, side):
        if contingent.status not in (
            ContingentStatus.FIGHTING,
            ContingentStatus.ROUTED,
        ):
            continue
        contingent.has_committed_reserves |= _should_commit(world, contingent, tuning)
        soldiers = troop_count(world, contingent)
        requests[contingent.faction_id] = (
            soldiers
            if contingent.has_committed_reserves
            else min(soldiers, contingent.desired_active)
        )
    return requests


def _deploy_contingent(
    world: WorldState, contingent: BattleContingent, target: int
) -> None:
    armies = contingent_armies(world, contingent)
    type_totals = {
        troop_type: sum(army.troops.get(troop_type, 0) for army in armies)
        for troop_type in TroopType
    }
    by_type = allocate_largest_remainder(target, type_totals)
    allocations = {
        troop_type: allocate_largest_remainder(
            by_type[troop_type],
            {army.id: army.troops.get(troop_type, 0) for army in armies},
        )
        for troop_type in TroopType
    }
    contingent.deployments = {
        army.id: _army_deployment(army.id, army.troops, allocations) for army in armies
    }


def _army_deployment(
    army_id: str,
    troops: dict[TroopType, int],
    allocations: dict[TroopType, dict[str, int]],
) -> ArmyDeployment:
    active = {troop_type: allocations[troop_type][army_id] for troop_type in troops}
    reserve = {
        troop_type: troops[troop_type] - active[troop_type] for troop_type in troops
    }
    return ArmyDeployment(
        army_id=army_id, available=dict(troops), active=active, reserve=reserve
    )


def reconcile_deployments(
    world: WorldState, battle: BattleState, tuning: BattleTuning
) -> None:
    """Rebuild authoritative partitions and cap the requests of all allies to one frontage."""
    for contingent in battle.contingents.values():
        contingent.deployments = {}
    for side in BattleSide:
        requests = _requests(world, battle, side, tuning)
        allocations = allocate_largest_remainder(
            tuning.frontage[battle.terrain], requests
        )
        for faction_id in sorted(allocations):
            _deploy_contingent(
                world, battle.contingents[faction_id], allocations[faction_id]
            )
