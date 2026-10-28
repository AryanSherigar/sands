from app.engine.coalitions.ledger import record_conquest
from app.engine.diplomacy.grounds import grant_ground
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
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
