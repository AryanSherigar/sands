from app.engine.battles.morale import should_withdraw, weighted_attribute
from app.engine.battles.retreat import resolve_retreats
from app.engine.battles.state import ExchangeRun, fighting_contingents, troop_count
from app.engine.economy.armies import remove_army
from app.models.world_battle import (
    BattleOutcome,
    BattleSide,
    BattleState,
    BattleStatus,
    ContingentStatus,
)
from app.models.world_state import WorldState


def remove_empty_armies(run: ExchangeRun) -> None:
    for army_id in sorted(run.accounting):
        army = run.world.armies.get(army_id)
        if army is not None and not sum(army.troops.values()):
            remove_army(run.world, army_id)
    for contingent in fighting_contingents(run.battle):
        if not troop_count(run.world, contingent):
            contingent.status = ContingentStatus.DESTROYED


def _has_opposing_fighters(run: ExchangeRun) -> bool:
    remaining = {
        contingent.side
        for contingent in fighting_contingents(run.battle)
        if troop_count(run.world, contingent)
    }
    return len(remaining) == len(BattleSide)


def resolve_policy_departures(run: ExchangeRun) -> None:
    if not _has_opposing_fighters(run):
        return
    tuning = run.scenario.tuning.battle
    withdrawing: set[str] = set()
    for contingent in fighting_contingents(run.battle):
        has_deployment = any(
            sum(deployment.active.values())
            for deployment in contingent.deployments.values()
        )
        if (
            weighted_attribute(run.world, contingent, "morale")
            <= tuning.forced_rout_morale
            or not has_deployment
        ):
            contingent.status = ContingentStatus.ROUTED
        should_leave = contingent.status == ContingentStatus.ROUTED or should_withdraw(
            run.world, contingent, tuning
        )
        if should_leave and contingent.faction_id not in run.excluded_attackers:
            withdrawing.add(contingent.faction_id)
    resolve_retreats(run, withdrawing, "policy")


def _side_outcome(battle: BattleState, defeated: BattleSide) -> BattleOutcome:
    has_surrender = any(
        contingent.side == defeated
        and contingent.status == ContingentStatus.SURRENDERED
        for contingent in battle.contingents.values()
    )
    if defeated == BattleSide.ATTACKER:
        return (
            BattleOutcome.ATTACKER_SURRENDER
            if has_surrender
            else BattleOutcome.DEFENDER_VICTORY
        )
    return (
        BattleOutcome.DEFENDER_SURRENDER
        if has_surrender
        else BattleOutcome.ATTACKER_VICTORY
    )


def _remaining_sides(world: WorldState, battle: BattleState) -> set[BattleSide]:
    return {
        contingent.side
        for contingent in fighting_contingents(battle)
        if troop_count(world, contingent)
    }


def reconcile_battle_outcome(
    world: WorldState, battle: BattleState, max_exchanges: int
) -> None:
    """Re-evaluate terminal state after globally arbitrated retreats without incrementing exchange counters."""
    remaining = _remaining_sides(world, battle)
    battle.outcome = None
    if len(remaining) == len(BattleSide):
        battle.status = (
            BattleStatus.AWAITING_NEXT_TURN
            if battle.exchanges_used >= max_exchanges
            else BattleStatus.AWAITING_COMMANDS
        )
        return
    battle.status = BattleStatus.RESOLVED
    battle.outcome = BattleOutcome.MUTUAL_DISENGAGEMENT
    if remaining:
        defeated = (
            BattleSide.DEFENDER
            if BattleSide.ATTACKER in remaining
            else BattleSide.ATTACKER
        )
        battle.outcome = _side_outcome(battle, defeated)


def finalize_exchange(run: ExchangeRun) -> None:
    run.battle.exchanges_used += 1
    run.battle.total_exchanges += 1
    reconcile_battle_outcome(
        run.world, run.battle, run.scenario.tuning.battle.max_exchanges_per_turn
    )
