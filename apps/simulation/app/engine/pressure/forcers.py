from app.engine.diplomacy.counters import next_counter
from app.models.world_pressure import MediationOffer, SubsidyState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _is_neutral(world: WorldState, mediator_id: FactionId, war_id: str) -> bool:
    war = next((item for item in world.wars if item.id == war_id), None)
    mediator = world.factions.get(mediator_id)
    if war is None or mediator is None or mediator.is_destroyed:
        return False
    sides = {war.attacker_id, war.defender_id, *war.participant_ids}
    return mediator_id not in sides and mediator.leader_id is not None


def has_open_offer(world: WorldState, war_id: str) -> bool:
    return any(
        offer.war_id == war_id and offer.expires_turn >= world.clock.turn
        for offer in world.pressure.mediation_offers
    )


def open_mediation(
    world: WorldState,
    scenario: StrategyScenario,
    mediator_id: FactionId,
    war_id: str,
) -> MediationOffer | None:
    if not world.pressure_ruleset or not _is_neutral(world, mediator_id, war_id):
        return None
    if has_open_offer(world, war_id):
        return None
    offer = MediationOffer(
        id=f"mediation_{next_counter(world, CounterKind.MEDIATION)}",
        mediator_id=mediator_id,
        war_id=war_id,
        expires_turn=world.clock.turn + scenario.tuning.pressure.mediation_ttl_turns,
    )
    world.pressure.mediation_offers.append(offer)
    return offer


def expire_mediation(world: WorldState) -> list[MediationOffer]:
    active_war_ids = {war.id for war in world.wars}
    kept = [
        offer
        for offer in world.pressure.mediation_offers
        if offer.expires_turn >= world.clock.turn and offer.war_id in active_war_ids
    ]
    removed = [o for o in world.pressure.mediation_offers if o not in kept]
    world.pressure.mediation_offers = kept
    return removed


def expire_subsidies(world: WorldState) -> list[SubsidyState]:
    active_war_ids = {war.id for war in world.wars}
    kept = [
        item
        for item in world.pressure.subsidies
        if item.expires_turn >= world.clock.turn and item.war_id in active_war_ids
    ]
    removed = [item for item in world.pressure.subsidies if item not in kept]
    world.pressure.subsidies = kept
    return removed
