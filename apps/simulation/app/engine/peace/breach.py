from app.engine.alliances.registry import alliance_between
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.opinion import opinion_of
from app.engine.pressure.wars import wars_of
from app.engine.rng import DeterministicRng
from app.engine.vassals.registry import vassalage_between
from app.models.world_diplomacy import CommitmentStatus, TruceState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_peace import BreachPressureState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    CedeRegionTerm,
    PayGoldTerm,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
)

PERCENT = 100
GRIEVANCE_FILED = "grievance_filed"


def _gold_taken(card: TermsCard, loser_id: FactionId) -> int:
    total = 0
    for term in card.terms:
        if isinstance(term, PayGoldTerm) and term.payer_id == loser_id:
            total += term.amount
        if isinstance(term, TributeTerm) and term.payer_id == loser_id:
            total += term.gold_per_turn * term.duration_turns
    return total


def ceded_regions(card: TermsCard, loser_id: FactionId) -> list[str]:
    return [
        term.region_id
        for term in card.terms
        if isinstance(term, CedeRegionTerm) and term.from_faction_id == loser_id
    ]


def card_harshness(
    world: WorldState, scenario: StrategyScenario, card: TermsCard, loser_id: FactionId
) -> int:
    tuning = scenario.tuning.peace
    ceded = ceded_regions(card, loser_id)
    owned = sum(1 for region in world.regions.values() if region.owner_id == loser_id)
    region_share = PERCENT * len(ceded) // max(1, owned)
    treasury = max(1, world.factions[loser_id].treasury)
    gold_share = min(PERCENT, PERCENT * _gold_taken(card, loser_id) // treasury)
    weighted = (
        region_share * tuning.harshness_region_percent
        + gold_share * (PERCENT - tuning.harshness_region_percent)
    ) // PERCENT
    is_capital_lost = world.factions[loser_id].capital_region_id in ceded
    bonus = tuning.harshness_capital_bonus if is_capital_lost else 0
    return min(PERCENT, weighted + bonus)


def recovery_gap(world: WorldState, faction_id: FactionId) -> int:
    return world.factions[faction_id].war_exhaustion


def _has_trade_deal(world: WorldState, truce: TruceState) -> bool:
    pair = {truce.faction_a, truce.faction_b}
    return any(
        commitment.status == CommitmentStatus.ACTIVE
        and isinstance(commitment.term, TradeDealTerm)
        and {commitment.term.faction_a, commitment.term.faction_b} == pair
        for commitment in world.commitments
    )


def _is_allied(world: WorldState, truce: TruceState) -> bool:
    if alliance_between(world, truce.faction_a, truce.faction_b) is not None:
        return True
    if vassalage_between(world, truce.faction_a, truce.faction_b) is not None:
        return True
    return any(
        (relation.faction_a, relation.faction_b) == (truce.faction_a, truce.faction_b)
        and relation.status == RelationStatus.ALLIANCE
        for relation in world.relations
    )


def _enemies(world: WorldState, faction_id: FactionId) -> set[str]:
    return {
        enemy
        for war in wars_of(world, faction_id)
        for enemy in (war.attacker_id, war.defender_id)
        if enemy != faction_id
    }


def _opinion_relief(
    world: WorldState, scenario: StrategyScenario, truce: TruceState
) -> int:
    if truce.loser_id is None:
        return 0
    winner_id = (
        truce.faction_b if truce.loser_id == truce.faction_a else truce.faction_a
    )
    loser_leader = world.factions[truce.loser_id].leader_id
    winner_leader = world.factions[winner_id].leader_id
    if loser_leader not in world.leaders:
        return 0
    opinion = opinion_of(world.leaders[loser_leader], winner_leader)
    return max(0, opinion) // scenario.tuning.peace.interaction_opinion_divisor


def interaction_relief(
    world: WorldState, scenario: StrategyScenario, truce: TruceState
) -> int:
    tuning = scenario.tuning.peace
    relief = _opinion_relief(world, scenario, truce)
    if _has_trade_deal(world, truce):
        relief += tuning.interaction_trade_relief
    if _is_allied(world, truce):
        relief += tuning.interaction_alliance_relief
    if any(hostage.truce_id == truce.id for hostage in world.peace.hostages):
        relief += tuning.interaction_hostage_relief
    if _enemies(world, truce.faction_a) & _enemies(world, truce.faction_b):
        relief += tuning.interaction_shared_enemy_relief
    return min(PERCENT, relief)


def breach_pressure(
    world: WorldState, scenario: StrategyScenario, truce: TruceState
) -> int:
    if truce.loser_id is None:
        return 0
    tuning = scenario.tuning.peace
    raw = (
        truce.harshness * tuning.harshness_weight
        + recovery_gap(world, truce.loser_id) * tuning.recovery_weight
    ) // PERCENT
    relief = interaction_relief(world, scenario, truce) * tuning.interaction_weight
    return max(0, min(PERCENT, raw - relief // PERCENT))


def _entry(world: WorldState, truce: TruceState) -> BreachPressureState:
    for entry in world.peace.breach:
        if (entry.faction_a, entry.faction_b) == (truce.faction_a, truce.faction_b):
            return entry
    entry = BreachPressureState(faction_a=truce.faction_a, faction_b=truce.faction_b)
    world.peace.breach.append(entry)
    return entry


def _grievance_ground(
    world: WorldState, scenario: StrategyScenario, truce: TruceState
) -> None:
    assert truce.loser_id is not None
    winner_id = (
        truce.faction_b if truce.loser_id == truce.faction_a else truce.faction_a
    )
    region_id = next(
        (
            region
            for region in truce.ceded_region_ids
            if world.regions[region].owner_id == winner_id
        ),
        None,
    )
    grant_ground(
        world,
        scenario,
        kind=GroundKind.CLAIM if region_id else GroundKind.INSULT,
        holder_faction_id=truce.loser_id,
        target_faction_id=winner_id,
        region_id=region_id,
    )


def _can_grieve(
    world: WorldState, scenario: StrategyScenario, truce: TruceState, entry
) -> bool:
    loser = world.factions.get(truce.loser_id or "")
    if loser is None or loser.is_destroyed or loser.leader_id is None:
        return False
    cooldown = scenario.tuning.peace.grievance_cooldown_turns
    is_cooled = entry.last_grievance_turn == 0 or (
        world.clock.turn - entry.last_grievance_turn >= cooldown
    )
    return is_cooled and world.clock.turn > 0


def tick_breach(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for truce in sorted(world.truces, key=lambda item: item.id):
        if truce.loser_id is None:
            continue
        entry = _entry(world, truce)
        entry.pressure = breach_pressure(world, scenario, truce)
        threshold = scenario.tuning.peace.grievance_pressure_threshold
        if entry.pressure < threshold or not _can_grieve(world, scenario, truce, entry):
            continue
        roll = rng.fork("grievance", truce.id, world.clock.turn).roll(PERCENT)
        if roll >= entry.pressure:
            continue
        _grievance_ground(world, scenario, truce)
        entry.last_grievance_turn = world.clock.turn
        events.append(
            diplomacy_event(
                GRIEVANCE_FILED,
                [truce.id, truce.loser_id],
                phase=PhaseName.TIME,
            )
        )
    return events
