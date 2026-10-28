from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.acceptance import does_counterpart_accept
from app.engine.peace.signing import is_white_peace_eligible, sign_peace
from app.engine.pressure.forcers import open_mediation
from app.models.orders import MediateOrder
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import PeaceTerm, TermsCard

MEDIATION_OFFERED = "mediation_offered"


def _white_peace_card(war: WarState, mediator_id: FactionId) -> TermsCard:
    peace = PeaceTerm(
        faction_a=war.attacker_id,
        faction_b=war.defender_id,
        tier=PeaceTier.SHORT,
        guarantor_ids=[mediator_id],
        is_white_peace=True,
    )
    return TermsCard(
        proposer_id=war.attacker_id,
        counterpart_id=war.defender_id,
        terms=[peace],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def _mirrored(card: TermsCard) -> TermsCard:
    return card.model_copy(
        update={"proposer_id": card.counterpart_id, "counterpart_id": card.proposer_id}
    )


def _try_white_peace(
    world: WorldState, scenario: StrategyScenario, war: WarState, mediator_id: FactionId
) -> list[EventLogEntry]:
    card = _white_peace_card(war, mediator_id)
    is_agreed = does_counterpart_accept(
        world, scenario, card, war
    ) and does_counterpart_accept(world, scenario, _mirrored(card), war)
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
