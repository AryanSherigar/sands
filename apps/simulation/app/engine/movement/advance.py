from app.engine.movement import events
from app.engine.movement.contact import Contact, ContactKind, classify_entry
from app.engine.movement.costs import LegCost, leg_cost
from app.engine.movement.engagement import armies_in_open_battle, open_or_join_battle
from app.engine.movement.state import MovementRun
from app.models.world_army import ArmyState, MarchState


def _current_cost(run: MovementRun, army: ArmyState, march: MarchState) -> LegCost:
    return leg_cost(
        run.index, army, run.world.clock, run.tuning, march.from_id, march.to_id
    )


def _continue_march(army: ArmyState, march: MarchState) -> None:
    if not march.route:
        army.march = None
        army.order = None
        return
    army.march = MarchState(
        from_id=march.to_id, to_id=march.route[0], route=march.route[1:]
    )


def _stop_march(army: ArmyState) -> None:
    army.march = None
    army.order = None


def _enter_region(
    run: MovementRun, army: ArmyState, march: MarchState, cost: LegCost
) -> bool:
    contact = classify_entry(run.world, army, march.to_id)
    if contact.kind is ContactKind.CONFRONTATION:
        _block_at_border(run, army, march)
        return True
    origin = army.location_id
    army.location_id = march.to_id
    kind = events.ARMY_ARRIVED if not march.route else events.ARMY_MOVED
    run.events.append(events.army_moved(kind, army.id, origin, march.to_id, cost))
    return _settle_contact(run, army, march, contact)


def _block_at_border(run: MovementRun, army: ArmyState, march: MarchState) -> None:
    run.events.append(
        events.contact(events.BORDER_CONFRONTATION, army.id, march.to_id, [])
    )
    _stop_march(army)


def _settle_contact(
    run: MovementRun, army: ArmyState, march: MarchState, contact: Contact
) -> bool:
    if contact.kind is ContactKind.BATTLE:
        defenders = list(contact.defender_ids)
        open_or_join_battle(run.world, march.to_id, [army.id], defenders)
        run.events.append(
            events.contact(events.CONTACT_BATTLE, army.id, march.to_id, defenders)
        )
        return True
    if contact.kind is ContactKind.ENEMY_REGION:
        run.events.append(
            events.contact(events.ENEMY_REGION_ENTERED, army.id, march.to_id, [])
        )
        _stop_march(army)
        return True
    _continue_march(army, march)
    return army.march is None


def _walk_back(
    run: MovementRun, army: ArmyState, march: MarchState, budget: int
) -> int | None:
    spend = min(budget, march.leg_progress)
    march.leg_progress -= spend
    if march.leg_progress > 0:
        run.events.append(events.army_returning(army.id, march.leg_progress))
        return None
    run.events.append(events.army_returned(army.id, army.location_id))
    _continue_after_return(army, march)
    return budget - spend


def _continue_after_return(army: ArmyState, march: MarchState) -> None:
    if not march.route:
        _stop_march(army)
        return
    army.march = MarchState(
        from_id=army.location_id, to_id=march.route[0], route=march.route[1:]
    )


def advance_army(run: MovementRun, army: ArmyState) -> None:
    budget = run.tuning.budget_per_turn
    while army.march is not None and not army.march.is_halted:
        march = army.march
        if march.is_returning:
            remaining = _walk_back(run, army, march, budget)
            if remaining is None:
                return
            budget = remaining
            continue
        cost = _current_cost(run, army, march)
        needed = max(0, cost.total - march.leg_progress)
        if needed > budget:
            march.leg_progress += budget
            run.events.append(
                events.army_en_route(army.id, march.to_id, march.leg_progress, cost)
            )
            return
        budget -= needed
        if _enter_region(run, army, march, cost):
            return


def advance_all(run: MovementRun) -> None:
    locked = armies_in_open_battle(run.world)
    for army_id, army in sorted(run.world.armies.items()):
        if army_id not in locked:
            advance_army(run, army)
