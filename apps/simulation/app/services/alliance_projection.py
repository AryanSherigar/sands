from app.engine.alliances.registry import active_alliances, alliance_term
from app.models.api_world_view import AllianceView, CallView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def project_alliances(world: WorldState, faction_id: FactionId) -> list[AllianceView]:
    views: list[AllianceView] = []
    for commitment in active_alliances(world, faction_id):
        term = alliance_term(commitment)
        partner_id = term.faction_b if term.faction_a == faction_id else term.faction_a
        views.append(
            AllianceView(
                id=commitment.id,
                partner_id=partner_id,
                alliance_type=term.alliance_type,
                ends_turn=commitment.end_turn,
                is_separate_peace_banned=term.is_separate_peace_banned,
            )
        )
    return views


def project_calls(world: WorldState, faction_id: FactionId) -> list[CallView]:
    return [
        CallView(
            id=call.id,
            caller_id=call.caller_id,
            war_id=call.war_id,
            side=call.side,
            is_defensive=call.is_defensive,
            deadline_turn=call.deadline_turn,
        )
        for call in sorted(world.alliance.calls, key=lambda item: item.id)
        if call.ally_id == faction_id
    ]
