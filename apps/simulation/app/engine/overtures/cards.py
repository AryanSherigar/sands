from app.engine.diplomacy.prisoners import ransom_price
from app.engine.negotiation import player_faction_id
from app.engine.overtures.pretexts import pretext_for
from app.engine.overtures.ransom import affordable_captives, pending_counter
from app.engine.overtures.renewals import renewal_truce_id
from app.engine.peace.signing import is_white_peace_eligible
from app.engine.pressure.wars import find_war, side_score
from app.models.world_diplomacy import WarState
from app.models.world_events import Overture
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    PayGoldTerm,
    PeaceTerm,
    PromiseKind,
    ReleasePrisonersTerm,
    SwornPromiseTerm,
    Term,
    TermsCard,
)

DEMAND_SHARE_DIVISOR = 2


def _short_peace(
    world: WorldState,
    scenario: StrategyScenario,
    npc_id: FactionId,
    war: WarState,
    *,
    is_bare: bool,
) -> PeaceTerm:
    return PeaceTerm(
        faction_a=npc_id,
        faction_b=player_faction_id(world),
        tier=PeaceTier.SHORT,
        is_white_peace=is_bare and is_white_peace_eligible(world, scenario, war),
    )


def _card(world: WorldState, npc_id: FactionId, terms: list[Term]) -> TermsCard:
    return TermsCard(
        proposer_id=npc_id,
        counterpart_id=player_faction_id(world),
        terms=terms,
        is_confirmed_by_counterpart=True,
    )


def peace_offer_card(
    world: WorldState, scenario: StrategyScenario, npc_id: FactionId
) -> TermsCard | None:
    war = find_war(world, npc_id, player_faction_id(world))
    if war is None:
        return None
    term = _short_peace(world, scenario, npc_id, war, is_bare=True)
    return _card(world, npc_id, [term])


def demand_card(
    world: WorldState, scenario: StrategyScenario, npc_id: FactionId
) -> TermsCard | None:
    player_id = player_faction_id(world)
    war = find_war(world, npc_id, player_id)
    if war is None:
        return None
    points = side_score(war, npc_id) // DEMAND_SHARE_DIVISOR
    affordable = points * scenario.tuning.peace.gold_per_score_point
    amount = min(world.factions[player_id].treasury, affordable)
    if amount <= 0:
        return None
    gold = PayGoldTerm(payer_id=player_id, payee_id=npc_id, amount=amount)
    term = _short_peace(world, scenario, npc_id, war, is_bare=False)
    return _card(world, npc_id, [term, gold])


def ransom_card(
    world: WorldState, scenario: StrategyScenario, npc_id: FactionId
) -> TermsCard | None:
    captives = affordable_captives(world, scenario, npc_id)
    if not captives:
        return None
    price = sum(ransom_price(item, scenario.tuning.peace) for item in captives)
    term = ReleasePrisonersTerm(
        holder_id=npc_id,
        recipient_id=player_faction_id(world),
        prisoner_ids=[item.id for item in captives],
        ransom_gold=price,
    )
    return _card(world, npc_id, [term])


def counter_card(world: WorldState, npc_id: FactionId) -> TermsCard | None:
    counter = pending_counter(world, npc_id)
    if counter is None:
        return None
    term = ReleasePrisonersTerm(
        holder_id=counter.holder_id,
        recipient_id=counter.origin_id,
        prisoner_ids=[counter.prisoner_id],
        ransom_gold=counter.gold,
    )
    return _card(world, npc_id, [term])


def oath_term(
    world: WorldState, scenario: StrategyScenario, npc_id: FactionId
) -> SwornPromiseTerm:
    return SwornPromiseTerm(
        promisor_id=npc_id,
        beneficiary_id=player_faction_id(world),
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=scenario.tuning.overtures.oath_offer_duration_turns,
    )


def oath_offer_card(
    world: WorldState, scenario: StrategyScenario, npc_id: FactionId
) -> TermsCard:
    return _card(world, npc_id, [oath_term(world, scenario, npc_id)])


def renewal_card(world: WorldState, faction_id: FactionId, truce_id: str) -> TermsCard:
    lapse = next(item for item in world.peace.lapses if item.truce_id == truce_id)
    term = PeaceTerm(
        faction_a=faction_id,
        faction_b=player_faction_id(world),
        tier=lapse.original_tier,
    )
    return _card(world, faction_id, [term])


def _card_for(
    world: WorldState,
    scenario: StrategyScenario,
    npc_id: FactionId,
    kind: OvertureKind,
) -> TermsCard | None:
    if kind is OvertureKind.PEACE_OFFER:
        return peace_offer_card(world, scenario, npc_id)
    if kind is OvertureKind.DEMAND:
        return demand_card(world, scenario, npc_id)
    if kind is OvertureKind.RANSOM_DEMAND:
        return ransom_card(world, scenario, npc_id)
    if kind is OvertureKind.RANSOM_COUNTER:
        return counter_card(world, npc_id)
    if kind is OvertureKind.OATH_OFFER:
        return oath_offer_card(world, scenario, npc_id)
    return None


def build_overture(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    kind: OvertureKind,
) -> Overture:
    leader = world.leaders[world.factions[faction_id].leader_id or ""]
    truce_id = renewal_truce_id(world, faction_id)
    if kind is OvertureKind.HEIR_RENEWAL and truce_id is not None:
        card = renewal_card(world, faction_id, truce_id)
    else:
        card, truce_id = _card_for(world, scenario, faction_id, kind), None
    return Overture(
        kind=kind,
        card=card,
        pretext=pretext_for(kind, leader, scenario),
        truce_id=truce_id,
    )
