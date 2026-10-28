from app.engine.battles.deployment import allocate_largest_remainder
from app.engine.battles.modifiers import attack_pressure, average_protection
from app.engine.battles.morale import apply_army_strain
from app.engine.battles.state import (
    PERCENT,
    ExchangeRun,
    exchange_rng,
    side_contingents,
)
from app.engine.outrage.effects import denies_quarter
from app.models.world_battle import BattleContingent, BattleSide, ContingentStatus
from strategy_contracts.battle import SupplyState
from strategy_contracts.enums import TroopType


def _active_cells(
    run: ExchangeRun, side: BattleSide
) -> dict[tuple[str, TroopType], int]:
    return {
        (army_id, troop_type): count
        for contingent in side_contingents(run.battle, side)
        if contingent.status in (ContingentStatus.FIGHTING, ContingentStatus.ROUTED)
        for army_id, deployment in sorted(contingent.deployments.items())
        for troop_type, count in sorted(deployment.active.items())
        if count
    }


def _side_pressure(run: ExchangeRun, side: BattleSide) -> int:
    return sum(
        attack_pressure(run.world, run.battle, contingent, run.scenario.tuning.battle)
        for contingent in side_contingents(run.battle, side)
        if contingent.status == ContingentStatus.FIGHTING
        and contingent.faction_id not in run.excluded_attackers
    )


def _side_protection(run: ExchangeRun, side: BattleSide) -> int:
    participants = [
        contingent
        for contingent in side_contingents(run.battle, side)
        if contingent.status in (ContingentStatus.FIGHTING, ContingentStatus.ROUTED)
    ]
    weights = {
        contingent.faction_id: sum(
            sum(deployment.active.values())
            for deployment in contingent.deployments.values()
        )
        for contingent in participants
    }
    return max(
        1,
        sum(
            weights[contingent.faction_id]
            * average_protection(run.battle, contingent, run.scenario.tuning.battle)
            for contingent in participants
        )
        // max(1, sum(weights.values())),
    )


def _losses_received(
    run: ExchangeRun, target_side: BattleSide
) -> dict[tuple[str, TroopType], int]:
    tuning = run.scenario.tuning.battle
    source_side = (
        BattleSide.DEFENDER
        if target_side == BattleSide.ATTACKER
        else BattleSide.ATTACKER
    )
    pressure = _side_pressure(run, source_side)
    cells = _active_cells(run, target_side)
    if not pressure or not cells:
        return {}
    rng = exchange_rng(run, source_side.value, "damage")
    numerator = (
        pressure
        * tuning.casualty_rate_percent
        * rng.roll_range(
            tuning.random_damage_min_percent, tuning.random_damage_max_percent
        )
    )
    denominator = PERCENT * PERCENT * _side_protection(run, target_side)
    losses, remainder = divmod(numerator, denominator)
    if remainder and rng.roll(denominator) < remainder:
        losses += 1
    return allocate_largest_remainder(min(losses, sum(cells.values())), cells)


def resolve_combat(run: ExchangeRun) -> None:
    """Calculate every loss against the frozen boundary before changing either side."""
    losses = {side: _losses_received(run, side) for side in BattleSide}
    for side in BattleSide:
        _apply_combat_losses(run, losses[side])
    _apply_strain(run)


def _apply_combat_losses(
    run: ExchangeRun, losses: dict[tuple[str, TroopType], int]
) -> None:
    for (army_id, troop_type), count in sorted(losses.items()):
        if count:
            run.world.armies[army_id].troops[troop_type] -= count
            run.accounting[army_id].combat_losses[troop_type] = count


def _faces_no_quarter(run: ExchangeRun, contingent: BattleContingent) -> bool:
    return any(
        denies_quarter(run.world, run.scenario, opponent.faction_id)
        for opponent in run.battle.contingents.values()
        if opponent.side != contingent.side
    )


def _apply_strain(run: ExchangeRun) -> None:
    if not all(_active_cells(run, side) for side in BattleSide):
        return
    for contingent in run.battle.contingents.values():
        if contingent.status not in (
            ContingentStatus.FIGHTING,
            ContingentStatus.ROUTED,
        ):
            continue
        for army_id in sorted(contingent.deployments):
            row = run.accounting[army_id]
            army = run.world.armies[army_id]
            apply_army_strain(
                army,
                sum(row.combat_losses.values()),
                sum(row.before.values()),
                contingent.supply or SupplyState.SUPPLIED,
                run.scenario.tuning.battle,
            )
            if _faces_no_quarter(run, contingent):
                bonus = run.scenario.tuning.outrage.no_quarter_morale_bonus
                army.morale = min(PERCENT, army.morale + bonus)
