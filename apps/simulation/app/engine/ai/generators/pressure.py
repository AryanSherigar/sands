from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import war_enemies
from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.coalitions.appease import offer_value
from app.engine.coalitions.registry import coalition_against
from app.engine.opinion import opinion_of
from app.engine.pacts import has_active_pact
from app.models.orders import AppeaseCoalitionOrder, MobilizeOrder
from app.models.world_state import WorldState
from strategy_contracts.coalition import (
    AppeaseOffer,
    ClaimCessionOffer,
    GoldOffer,
    PactOffer,
)
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory


def _is_cornered(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    enemies = war_enemies(world, faction_id)
    has_occupied_region = any(
        region.owner_id == faction_id
        and region.occupation is not None
        and region.occupation.occupier_id in enemies
        for region in world.regions.values()
    )
    if has_occupied_region:
        return True
    return any(
        known_power_ratio(world, scenario, faction_id, enemy_id) < FULL_PERCENT
        for enemy_id in enemies
    )


def mobilize_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    if not scenario.toggles.is_ai_pressure_enabled:
        return []
    if not war_enemies(world, faction_id):
        return []
    if world.factions[faction_id].stability <= tuning.low_stability:
        return []
    base = -tuning.mobilize_friction
    if _is_cornered(world, scenario, faction_id):
        base += tuning.mobilize_cornered_bonus
    return [Candidate(MobilizeOrder(faction_id=faction_id), ScoreCategory.ATTACK, base)]


def _estimated_price(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    member_id: FactionId,
) -> int:
    tuning = scenario.tuning.coalition
    own_leader = world.leaders[world.factions[faction_id].leader_id]
    member_leader_id = world.factions[member_id].leader_id
    resentment = max(
        0, tuning.join_opinion_below - opinion_of(own_leader, member_leader_id)
    )
    price = tuning.appease_base_price + tuning.appease_opinion_weight * resentment
    margin = FULL_PERCENT + scenario.tuning.ai.appease_safety_margin_percent
    return price * margin // FULL_PERCENT


def _gold_needed(scenario: StrategyScenario, price: int) -> int:
    percent = scenario.tuning.coalition.appease_gold_value_percent
    if percent <= 0:
        return 0
    return max(1, -(-price * FULL_PERCENT // percent))


def _cession_offers(
    world: WorldState, faction_id: FactionId, member_id: FactionId
) -> list[AppeaseOffer]:
    capital_id = world.factions[faction_id].capital_region_id
    return [
        ClaimCessionOffer(region_id=region.id)
        for region in sorted(world.regions.values(), key=lambda item: item.id)
        if region.owner_id == faction_id
        and member_id in region.claimant_ids
        and region.id != capital_id
    ]


def _offer_options(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    member_id: FactionId,
    price: int,
) -> list[AppeaseOffer]:
    options: list[AppeaseOffer] = []
    if not has_active_pact(world, faction_id, member_id):
        pact_turns = scenario.tuning.coalition.appease_max_pact_turns
        options.append(PactOffer(duration_turns=pact_turns))
    gold = _gold_needed(scenario, price)
    if 0 < gold <= world.factions[faction_id].treasury:
        options.append(GoldOffer(amount=gold))
    options.extend(_cession_offers(world, faction_id, member_id))
    return options


def _cheapest_covering_offer(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    member_id: FactionId,
) -> AppeaseOffer | None:
    price = _estimated_price(world, scenario, faction_id, member_id)
    for offer in _offer_options(world, scenario, faction_id, member_id, price):
        if offer_value(world, scenario, offer) >= price:
            return offer
    return None


def appease_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    if not scenario.toggles.is_ai_pressure_enabled:
        return []
    coalition = coalition_against(world, faction_id)
    if coalition is None:
        return []
    candidates: list[Candidate] = []
    for member_id in sorted(coalition.member_ids):
        offer = _cheapest_covering_offer(world, scenario, faction_id, member_id)
        if offer is None:
            continue
        order = AppeaseCoalitionOrder(
            faction_id=faction_id, member_id=member_id, offer=offer
        )
        candidates.append(
            Candidate(order, ScoreCategory.ALLY, scenario.tuning.ai.appease_bonus)
        )
    return candidates
