from app.engine.vassals.registry import active_vassalages, vassal_term
from app.models.api_world_view import PendingDemandView, VassalageView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def project_vassalages(world: WorldState, faction_id: FactionId) -> list[VassalageView]:
    views: list[VassalageView] = []
    for commitment in active_vassalages(world, faction_id):
        term = vassal_term(commitment)
        views.append(
            VassalageView(
                id=commitment.id,
                overlord_id=term.overlord_id,
                vassal_id=term.vassal_id,
                tribute_share_percent=term.tribute_share_percent,
                levy_share_percent=term.levy_share_percent,
                is_foreign_policy_controlled=term.is_foreign_policy_controlled,
                has_garrison_rights=term.has_garrison_rights,
                ends_turn=commitment.end_turn,
            )
        )
    return views


def project_pending_demands(
    world: WorldState, faction_id: FactionId
) -> list[PendingDemandView]:
    return [
        PendingDemandView(
            id=demand.id,
            overlord_id=demand.overlord_id,
            kind=demand.kind,
            amount=demand.amount,
            granted=demand.granted,
            deadline_turn=demand.deadline_turn,
        )
        for demand in sorted(world.vassal.demands, key=lambda item: item.id)
        if demand.vassal_id == faction_id
    ]
