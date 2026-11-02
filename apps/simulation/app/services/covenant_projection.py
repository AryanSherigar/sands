from app.models.api_world_view import CovenantView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.revolt import CovenantStatus


def project_covenants(world: WorldState, faction_id: FactionId) -> list[CovenantView]:
    return [
        CovenantView(
            covenant_id=covenant.id,
            region_id=covenant.region_id,
            covenant=covenant.covenant,
            end_turn=covenant.end_turn,
        )
        for covenant in world.covenants
        if covenant.status is CovenantStatus.ACTIVE
        and covenant.faction_id == faction_id
    ]
