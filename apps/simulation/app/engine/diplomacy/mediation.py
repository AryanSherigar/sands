from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.acceptance import does_counterpart_accept
from app.engine.peace.bare_peace import build_bare_peace_card, mirror_card
from app.engine.peace.signing import is_white_peace_eligible, sign_peace
from app.engine.pressure.forcers import open_mediation
from app.models.orders import MediateOrder
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

MEDIATION_OFFERED = "mediation_offered"


def _try_white_peace(
    world: WorldState, scenario: StrategyScenario, war: WarState, mediator_id: FactionId
) -> list[EventLogEntry]:
    card = build_bare_peace_card(
        war, war.attacker_id, war.defender_id, [mediator_id], is_white_peace=True
    )
    is_agreed = does_counterpart_accept(
        world, scenario, card, war
    ) and does_counterpart_accept(world, scenario, mirror_card(card), war)
    if not is_agreed or not is_white_peace_eligible(world, scenario, war):
        return []
    return sign_peace(world, scenario, card, f"mediation-{war.id}")


def apply_mediation(
    world: WorldState, scenario: StrategyScenario, order: MediateOrder
) -> list[EventLogEntry]:
    """Open the offer; a player mediating a war between two NPCs can end it in a white peace."""
    offer = open_mediation(world, scenario, order.faction_id, order.war_id)
    assert offer is not None
    events = [
        diplomacy_event(MEDIATION_OFFERED, [offer.id, order.faction_id, order.war_id])
    ]
    war = next(item for item in world.wars if item.id == order.war_id)
    is_player = world.factions[order.faction_id].is_player
    if is_player and not any(
        world.factions[f].is_player for f in (war.attacker_id, war.defender_id)
    ):
        events += _try_white_peace(world, scenario, war, order.faction_id)
    return events
