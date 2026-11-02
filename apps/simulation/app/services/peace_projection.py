from app.engine.diplomacy.war_score import goal_slots
from app.engine.pressure.wars import side_score
from app.models.api_world_view import (
    HostageView,
    MediationOfferView,
    TruceView,
    WarView,
)
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from app.services.peace_brief import STANDING_MARGIN
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario


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


def _player_edge(war: WarState, faction_id: FactionId) -> int | None:
    if faction_id not in (war.attacker_id, war.defender_id):
        return None
    own = side_score(war, faction_id)
    total = war.war_score_attacker + war.war_score_defender
    return own - (total - own)


def _outlook(edge: int | None) -> str:
    if edge is None or abs(edge) < STANDING_MARGIN:
        return "even"
    return "leading" if edge > 0 else "trailing"


def _own_goal_slots(
    war: WarState, faction_id: FactionId, scenario: StrategyScenario
) -> int:
    if _player_edge(war, faction_id) is None:
        return 1
    return goal_slots(side_score(war, faction_id), scenario.tuning.diplomacy)


def project_wars(
    world: WorldState, faction_id: FactionId, scenario: StrategyScenario
) -> list[WarView]:
    return [
        WarView(
            id=war.id,
            attacker_id=war.attacker_id,
            defender_id=war.defender_id,
            participant_ids=list(war.participant_ids),
            outlook=_outlook(_player_edge(war, faction_id)),
            goal_slots=_own_goal_slots(war, faction_id, scenario),
        )
        for war in sorted(world.wars, key=lambda item: item.id)
        if faction_id in (war.attacker_id, war.defender_id, *war.participant_ids)
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
