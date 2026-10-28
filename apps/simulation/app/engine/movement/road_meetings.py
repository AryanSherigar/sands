from app.engine.movement import events
from app.engine.movement.contact import relation_status
from app.engine.movement.costs import leg_cost
from app.engine.movement.engagement import armies_in_open_battle, open_or_join_battle
from app.engine.movement.state import MovementRun
from app.models.world_army import ArmyState, MarchState
from strategy_contracts.enums import RelationStatus


def _leg_cost_total(run: MovementRun, army: ArmyState, march: MarchState) -> int:
    return leg_cost(
        run.index, army, run.world.clock, run.tuning, march.from_id, march.to_id
    ).total


def _head_on_marches(
    left: ArmyState, right: ArmyState
) -> tuple[MarchState, MarchState] | None:
    left_march, right_march = left.march, right.march
    if left_march is None or right_march is None:
        return None
    if left_march.leg_progress == 0 or right_march.leg_progress == 0:
        return None
    if left_march.is_returning or right_march.is_returning:
        return None
    is_opposite = (left_march.from_id, left_march.to_id) == (
        right_march.to_id,
        right_march.from_id,
    )
    return (left_march, right_march) if is_opposite else None


def _have_met(
    run: MovementRun,
    left: ArmyState,
    right: ArmyState,
    marches: tuple[MarchState, MarchState],
) -> bool:
    left_march, right_march = marches
    left_cost = _leg_cost_total(run, left, left_march)
    right_cost = _leg_cost_total(run, right, right_march)
    covered = (
        left_march.leg_progress * right_cost + right_march.leg_progress * left_cost
    )
    return covered >= left_cost * right_cost


def _meet(run: MovementRun, left: ArmyState, right: ArmyState) -> None:
    region_id = left.location_id
    right.location_id = region_id
    open_or_join_battle(run.world, region_id, [left.id], [right.id])
    run.events.append(
        events.contact(events.ROAD_MEETING, left.id, region_id, [right.id])
    )


def resolve_road_meetings(run: MovementRun) -> None:
    busy = armies_in_open_battle(run.world)
    on_road = [
        army
        for _, army in sorted(run.world.armies.items())
        if army.march is not None and army.id not in busy
    ]
    for position, left in enumerate(on_road):
        for right in on_road[position + 1 :]:
            if _is_meeting(run, left, right):
                _meet(run, left, right)


def _is_meeting(run: MovementRun, left: ArmyState, right: ArmyState) -> bool:
    status = relation_status(run.world, left.owner_id, right.owner_id)
    marches = _head_on_marches(left, right)
    if status is not RelationStatus.WAR or marches is None:
        return False
    return _have_met(run, left, right, marches)
