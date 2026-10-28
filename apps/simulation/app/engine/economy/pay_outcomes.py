from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT, ceil_division, clamp
from app.engine.economy.armies import remove_army
from app.engine.economy.state import EconomyRun
from app.models.world_army import ArmyState
from app.models.world_events import StateChange


def _is_resting(run: EconomyRun, army: ArmyState) -> bool:
    region = run.world.regions.get(army.location_id)
    is_home = region is not None and region.owner_id == army.owner_id
    return is_home and army.march is None and army.id not in run.battle_army_ids


def _set_morale(army: ArmyState, morale: int) -> StateChange:
    change = StateChange(
        path=f"armies.{army.id}.morale", before=army.morale, after=morale
    )
    army.morale = morale
    return change


def apply_paid(run: EconomyRun, army: ArmyState) -> None:
    army.unpaid_turns = 0
    if not _is_resting(run, army):
        return
    gain = run.tuning.morale_recovery[army.pay_level]
    morale = clamp(army.morale + gain, 0, PERCENT)
    if morale != army.morale:
        change = _set_morale(army, morale)
        run.events.append(events.army_rested(army.id, morale - change.before, change))


def _desert(run: EconomyRun, army: ArmyState) -> None:
    lost: dict[str, int] = {}
    changes: list[StateChange] = []
    for troop_type, count in sorted(
        army.troops.items(), key=lambda item: item[0].value
    ):
        loss = min(count, ceil_division(count * run.tuning.desertion_percent, PERCENT))
        if loss == 0:
            continue
        army.troops[troop_type] = count - loss
        lost[troop_type.value] = loss
        changes.append(
            StateChange(
                path=f"armies.{army.id}.troops.{troop_type.value}",
                before=count,
                after=count - loss,
            )
        )
    run.events.append(events.army_deserted(army.id, lost, changes))


def apply_unpaid(run: EconomyRun, army: ArmyState) -> None:
    army.unpaid_turns += 1
    morale = clamp(army.morale - run.tuning.unpaid_morale_loss, 0, PERCENT)
    loss = army.morale - morale
    change = _set_morale(army, morale)
    run.events.append(events.army_unpaid(army.id, army.unpaid_turns, loss, change))
    if army.unpaid_turns >= run.tuning.desertion_after_unpaid_turns:
        _desert(run, army)
    if sum(army.troops.values()) == 0:
        remove_army(run.world, army.id)
        run.events.append(events.army_dissolved(army.id))
