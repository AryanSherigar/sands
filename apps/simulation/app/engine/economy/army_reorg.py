from app.engine.economy import events
from app.engine.economy.armies import next_army_id, remove_army
from app.engine.economy.reasons import RejectReason
from app.engine.economy.state import EconomyRun
from app.models.orders import MergeArmiesOrder, SetArmyPolicyOrder, SplitArmyOrder
from app.models.world_army import ArmyState
from strategy_contracts.enums import TroopType
from strategy_contracts.ids import ArmyId, FactionId


def _is_busy(run: EconomyRun, army: ArmyState) -> bool:
    is_besieging = any(army.id in siege.army_ids for siege in run.world.sieges)
    return army.march is not None or army.order is not None or is_besieging


def _army_problem(
    run: EconomyRun, army_id: ArmyId, faction_id: FactionId
) -> RejectReason | None:
    army = run.world.armies.get(army_id)
    if army is None:
        return RejectReason.UNKNOWN_ARMY
    if army.owner_id != faction_id:
        return RejectReason.NOT_YOUR_ARMY
    if army_id in run.battle_army_ids:
        return RejectReason.IN_BATTLE
    if _is_busy(run, army):
        return RejectReason.ARMY_BUSY
    return None


def _merge_problem(run: EconomyRun, order: MergeArmiesOrder) -> RejectReason | None:
    ids = list(dict.fromkeys(order.army_ids))
    if len(ids) != len(order.army_ids) or order.into_army_id not in ids:
        return RejectReason.INVALID_MERGE
    for army_id in ids:
        problem = _army_problem(run, army_id, order.faction_id)
        if problem is not None:
            return problem
    locations = {run.world.armies[army_id].location_id for army_id in ids}
    return RejectReason.DIFFERENT_LOCATION if len(locations) > 1 else None


def _weighted(armies: list[ArmyState], field: str) -> int:
    total = sum(sum(army.troops.values()) for army in armies)
    if total == 0:
        return getattr(armies[0], field)
    weighted = sum(getattr(army, field) * sum(army.troops.values()) for army in armies)
    return weighted // total


def apply_merge(run: EconomyRun, order: MergeArmiesOrder) -> None:
    problem = _merge_problem(run, order)
    if problem is not None:
        run.events.append(events.order_rejected(order.into_army_id, problem.value))
        return
    armies = [run.world.armies[army_id] for army_id in order.army_ids]
    target = run.world.armies[order.into_army_id]
    troops: dict[TroopType, int] = {}
    for army in armies:
        for kind, count in army.troops.items():
            troops[kind] = troops.get(kind, 0) + count
    target.morale = _weighted(armies, "morale")
    target.fatigue = _weighted(armies, "fatigue")
    target.unpaid_turns = max(army.unpaid_turns for army in armies)
    target.troops = troops
    merged_ids = [army.id for army in armies if army.id != target.id]
    for army_id in merged_ids:
        remove_army(run.world, army_id)
    run.events.append(
        events.armies_merged(
            order.faction_id, target.id, merged_ids, sum(troops.values())
        )
    )


def apply_set_policy(run: EconomyRun, order: SetArmyPolicyOrder) -> None:
    army = run.world.armies.get(order.army_id)
    if army is None or army.owner_id != order.faction_id:
        reason = (
            RejectReason.UNKNOWN_ARMY if army is None else RejectReason.NOT_YOUR_ARMY
        )
        run.events.append(events.order_rejected(order.army_id, reason.value))
        return
    if order.army_id in run.battle_army_ids:
        run.events.append(
            events.order_rejected(order.army_id, RejectReason.IN_BATTLE.value)
        )
        return
    if order.withdrawal_policy is not None:
        army.withdrawal_policy = order.withdrawal_policy
    if order.reserve_policy is not None:
        army.reserve_policy = order.reserve_policy


def _split_problem(run: EconomyRun, order: SplitArmyOrder) -> RejectReason | None:
    problem = _army_problem(run, order.army_id, order.faction_id)
    if problem is not None:
        return problem
    army = run.world.armies[order.army_id]
    taken = {kind: count for kind, count in order.troops.items() if count > 0}
    is_overdrawn = any(
        count > army.troops.get(kind, 0) for kind, count in taken.items()
    )
    is_empty = sum(taken.values()) == 0
    leaves_nothing = sum(taken.values()) >= sum(army.troops.values())
    if is_overdrawn or is_empty or leaves_nothing:
        return RejectReason.INVALID_SPLIT
    return None


def apply_split(run: EconomyRun, order: SplitArmyOrder) -> None:
    problem = _split_problem(run, order)
    if problem is not None:
        run.events.append(events.order_rejected(order.army_id, problem.value))
        return
    parent = run.world.armies[order.army_id]
    taken = {kind: count for kind, count in order.troops.items() if count > 0}
    for kind, count in taken.items():
        parent.troops[kind] -= count
    parent.troops = {kind: count for kind, count in parent.troops.items() if count > 0}
    child = ArmyState(
        id=next_army_id(run.world),
        owner_id=parent.owner_id,
        troops=taken,
        morale=parent.morale,
        fatigue=parent.fatigue,
        location_id=parent.location_id,
        pay_level=parent.pay_level,
        unpaid_turns=parent.unpaid_turns,
    )
    run.world.armies[child.id] = child
    run.events.append(
        events.army_split(order.faction_id, parent.id, child.id, sum(taken.values()))
    )
