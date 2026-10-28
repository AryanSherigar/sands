from app.models.api_world_view import HostageView, MediationOfferView, TruceView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier


def project_truces(world: WorldState, faction_id: FactionId) -> list[TruceView]:
    return [
        TruceView(
            faction_a=truce.faction_a,
            faction_b=truce.faction_b,
            tier=truce.tier,
            expires_turn=None
            if truce.tier is PeaceTier.PERPETUAL
            else truce.expires_turn,
            is_fragile=truce.is_fragile,
            guarantor_ids=list(truce.guarantor_ids),
        )
        for truce in sorted(world.truces, key=lambda item: item.id)
        if faction_id in (truce.faction_a, truce.faction_b)
    ]


def project_hostages(world: WorldState, faction_id: FactionId) -> list[HostageView]:
    return [
        HostageView(
            id=hostage.id,
            giver_id=hostage.giver_id,
            holder_id=hostage.holder_id,
            leader_id=hostage.leader_id,
            release_turn=hostage.release_turn,
            is_at_mercy=hostage.is_at_mercy,
        )
        for hostage in sorted(world.peace.hostages, key=lambda item: item.id)
        if faction_id in (hostage.giver_id, hostage.holder_id)
    ]


def project_mediations(
    world: WorldState, faction_id: FactionId
) -> list[MediationOfferView]:
    own_war_ids = {
        war.id
        for war in world.wars
        if faction_id in (war.attacker_id, war.defender_id, *war.participant_ids)
    }
    return [
        MediationOfferView(
            id=offer.id,
            mediator_id=offer.mediator_id,
            war_id=offer.war_id,
            expires_turn=offer.expires_turn,
        )
        for offer in sorted(world.pressure.mediation_offers, key=lambda item: item.id)
        if offer.war_id in own_war_ids or offer.mediator_id == faction_id
    ]
