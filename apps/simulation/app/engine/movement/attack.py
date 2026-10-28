from app.engine.movement.contact import ContactKind, classify_entry, relation_status
from app.engine.movement.knowledge import visible_regions
from app.engine.movement.reasons import RejectReason
from app.engine.movement.state import MovementRun
from app.models.world_army import ArmyState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import RegionId


def _owner_is_at_war(run: MovementRun, army: ArmyState, region_id: RegionId) -> bool:
    owner_id = run.world.regions[region_id].owner_id
    if owner_id is None:
        return False
    return relation_status(run.world, army.owner_id, owner_id) is RelationStatus.WAR


def _sees_hostile_army(run: MovementRun, army: ArmyState, region_id: RegionId) -> bool:
    visible = visible_regions(run.world, army.owner_id, run.index)
    if region_id not in visible:
        return False
    return classify_entry(run.world, army, region_id).kind is ContactKind.BATTLE


def attack_problem(
    run: MovementRun, army: ArmyState, region_id: RegionId
) -> RejectReason | None:
    """Judge a target only by what its owner can know: a hidden army never makes a region a valid target."""
    if region_id not in run.world.regions:
        return RejectReason.UNKNOWN_REGION
    if _owner_is_at_war(run, army, region_id) or _sees_hostile_army(
        run, army, region_id
    ):
        return None
    return RejectReason.TARGET_NOT_HOSTILE
