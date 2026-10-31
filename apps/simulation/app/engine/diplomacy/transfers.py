from app.engine.coalitions.ledger import record_conquest
from app.engine.diplomacy.grounds import grant_ground
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm


def cede_region(
    world: WorldState, scenario: StrategyScenario, term: CedeRegionTerm
) -> None:
    region = world.regions[term.region_id]
    region.owner_id = term.to_faction_id
    record_conquest(world, scenario, term.to_faction_id, term.region_id)
    if term.from_faction_id not in region.claimant_ids:
        region.claimant_ids = sorted([*region.claimant_ids, term.from_faction_id])
    previous = world.factions[term.from_faction_id]
    if previous.leader_id is not None and not previous.is_destroyed:
        grant_ground(
            world,
            scenario,
            kind=GroundKind.CLAIM,
            holder_faction_id=term.from_faction_id,
            target_faction_id=term.to_faction_id,
            region_id=term.region_id,
        )


def pay_gold(world: WorldState, term: PayGoldTerm) -> None:
    payer = world.factions[term.payer_id]
    amount = min(term.amount, payer.treasury)
    payer.treasury -= amount
    world.factions[term.payee_id].treasury += amount


def hand_over_region(
    world: WorldState,
    region_id: RegionId,
    from_faction_id: FactionId,
    to_faction_id: FactionId,
) -> None:
    region = world.regions[region_id]
    region.owner_id = to_faction_id
    region.claimant_ids = [
        claimant for claimant in region.claimant_ids if claimant != to_faction_id
    ]
    world.grounds = [
        ground
        for ground in world.grounds
        if not (
            ground.kind is GroundKind.CLAIM
            and ground.region_id == region_id
            and ground.holder_faction_id == to_faction_id
        )
    ]
