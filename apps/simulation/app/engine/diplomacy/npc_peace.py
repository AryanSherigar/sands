from app.engine.diplomacy.collapse_settlement import collapse_cession, is_collapsed
from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.acceptance import does_counterpart_accept
from app.engine.peace.bare_peace import build_bare_peace_card
from app.engine.peace.signing import is_white_peace_eligible, sign_peace
from app.engine.pressure.wars import side_score
from app.models.orders import SuePeaceOrder
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import TermsCard

PEACE_SUED = "peace_sued"
PEACE_REFUSED = "peace_refused"


def find_war_by_id(world: WorldState, war_id: str) -> WarState | None:
    return next((war for war in world.wars if war.id == war_id), None)


def other_belligerent(war: WarState, faction_id: FactionId) -> FactionId:
    return war.defender_id if faction_id == war.attacker_id else war.attacker_id


def _peace_card(
    world: WorldState, scenario: StrategyScenario, war: WarState, proposer_id: FactionId
) -> TermsCard:
    counterpart_id = other_belligerent(war, proposer_id)
    card = build_bare_peace_card(
        war,
        proposer_id,
        counterpart_id,
        [],
        is_white_peace=is_white_peace_eligible(world, scenario, war),
    )
    if not is_collapsed(world, scenario, proposer_id):
        return card
    cession = collapse_cession(world, scenario, war, proposer_id, counterpart_id)
    if cession is None:
        return card
    return card.model_copy(update={"terms": [*card.terms, cession]})


def apply_sue_peace(
    world: WorldState, scenario: StrategyScenario, order: SuePeaceOrder
) -> list[EventLogEntry]:
    """An NPC offers its enemy a bare peace; the war ends only if the enemy accepts.

    NOTE: a stalemate gets a white peace. A decided war gets a short peace the
    leading side can afford, so only the leader's offer can succeed there.
    """
    war = find_war_by_id(world, order.war_id)
    assert war is not None
    card = _peace_card(world, scenario, war, order.faction_id)
    subjects = [order.faction_id, card.counterpart_id, war.id]
    is_leading = side_score(war, order.faction_id) > side_score(
        war, card.counterpart_id
    )
    is_stalemate = is_white_peace_eligible(world, scenario, war)
    is_surrender = is_collapsed(world, scenario, order.faction_id)
    is_agreed = (
        is_stalemate or is_leading or is_surrender
    ) and does_counterpart_accept(world, scenario, card, war)
    if not is_agreed:
        return [diplomacy_event(PEACE_REFUSED, subjects)]
    return [
        diplomacy_event(PEACE_SUED, subjects),
        *sign_peace(world, scenario, card, f"sue-peace-{war.id}"),
    ]
