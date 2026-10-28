from app.engine.coalitions.threat import compute_threat
from app.engine.pressure.bands import to_band
from app.models.api_world_view import CoalitionView, OwnThreatView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def project_coalitions(world: WorldState, faction_id: FactionId) -> list[CoalitionView]:
    if world.coalition_ruleset < 1:
        return []
    return [
        CoalitionView(
            id=coalition.id,
            target_id=coalition.target_id,
            member_ids=sorted(coalition.member_ids),
            expires_turn=coalition.expires_turn,
        )
        for coalition in sorted(world.coalition.coalitions, key=lambda item: item.id)
        if faction_id == coalition.target_id or faction_id in coalition.member_ids
    ]


def project_own_threat(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> OwnThreatView | None:
    if world.coalition_ruleset < 1:
        return None
    reading = compute_threat(world, scenario, faction_id)
    return OwnThreatView(
        band=to_band(reading.value, scenario.tuning.pressure),
        factors={
            "conquest": reading.conquest,
            "treaty_breaking": reading.treaty_breaking,
            "atrocity": reading.atrocity,
            "balance": reading.balance,
        },
    )
