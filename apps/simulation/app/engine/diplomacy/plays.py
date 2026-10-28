from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.transfers import cede_region, pay_gold
from app.engine.diplomacy.validation import is_at_war
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.negotiation import memory_warmth, opinion_of
from app.engine.negotiation_memory import record_talks_memory
from app.engine.outrage.demands import react_to_demand
from app.engine.trait_axes import axis_totals
from app.models.orders import CallNegotiationOrder, DeclareWarOrder, DiplomaticPlayOrder
from app.models.world_diplomacy import DiplomaticPlayState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm, TermsCard
from strategy_contracts.traits import TraitAxis

FULL_PERCENT = 100


def open_play(
    world: WorldState,
    scenario: StrategyScenario,
    order: DiplomaticPlayOrder | CallNegotiationOrder,
) -> list[EventLogEntry]:
    is_demand = isinstance(order, DiplomaticPlayOrder)
    play = DiplomaticPlayState(
        id=f"play_{next_counter(world, CounterKind.PLAY)}",
        attacker_id=order.faction_id,
        defender_id=order.target_faction_id,
        demands=list(order.demands) if is_demand else [],
        stage="demand",
        kind="demand" if is_demand else "talks",
        due_turn=world.clock.turn + 1,
    )
    world.plays.append(play)
    events = [
        diplomacy_event(
            "play_opened", [play.id, order.faction_id, order.target_faction_id]
        )
    ]
    if is_demand:
        events += _react_to_play_demand(world, scenario, order)
    return events


def _react_to_play_demand(
    world: WorldState, scenario: StrategyScenario, order: DiplomaticPlayOrder
) -> list[EventLogEntry]:
    if not order.demands:
        return []
    card = TermsCard(
        proposer_id=order.faction_id,
        counterpart_id=order.target_faction_id,
        terms=list(order.demands),
    )
    return react_to_demand(
        world, scenario, demander_id=order.faction_id, card=card, tone_grade=None
    )


def _troops(world: WorldState, faction_id: str) -> int:
    return sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == faction_id
    )


def _defender_worth(world: WorldState, faction_id: str) -> int:
    wealth = sum(
        region.wealth
        for region in world.regions.values()
        if region.owner_id == faction_id
    )
    return world.factions[faction_id].treasury + wealth


def _demand_price(world: WorldState, play: DiplomaticPlayState) -> int:
    price = 0
    for term in play.demands:
        if isinstance(term, PayGoldTerm):
            price += term.amount
        elif isinstance(term, CedeRegionTerm):
            price += world.regions[term.region_id].wealth
    return price


def demand_price_percent(world: WorldState, play: DiplomaticPlayState) -> int:
    worth = max(1, _defender_worth(world, play.defender_id))
    return FULL_PERCENT * _demand_price(world, play) // worth


def demand_limit_percent(
    world: WorldState, scenario: StrategyScenario, play: DiplomaticPlayState
) -> int:
    tuning = scenario.tuning.diplomacy
    leader = world.leaders[world.factions[play.defender_id].leader_id or ""]
    totals = axis_totals(leader, scenario)
    temper = totals[TraitAxis.CAUTION] + totals[TraitAxis.TRUST]
    temper -= totals[TraitAxis.PRIDE] + totals[TraitAxis.AGGRESSION]
    leverage = FULL_PERCENT * _troops(world, play.attacker_id)
    leverage //= max(1, _troops(world, play.defender_id))
    limit = tuning.demand_base_limit_percent + tuning.demand_axis_step * temper
    limit += (leverage - FULL_PERCENT) // tuning.demand_leverage_divisor
    return min(max(limit, 0), tuning.demand_limit_max_percent)


def _concede(
    world: WorldState, scenario: StrategyScenario, play: DiplomaticPlayState
) -> list[EventLogEntry]:
    for term in play.demands:
        if isinstance(term, CedeRegionTerm):
            cede_region(world, scenario, term)
        elif isinstance(term, PayGoldTerm):
            pay_gold(world, term)
    return [diplomacy_event("play_conceded", [play.id, play.defender_id])]


def _refuse(
    world: WorldState, scenario: StrategyScenario, play: DiplomaticPlayState
) -> list[EventLogEntry]:
    events = [diplomacy_event("play_refused", [play.id, play.defender_id])]
    attacker = world.factions[play.attacker_id]
    if attacker.is_destroyed or attacker.leader_id is None:
        return events
    if is_at_war(world, play.attacker_id, play.defender_id):
        return events
    ground = grant_ground(
        world,
        scenario,
        kind=GroundKind.REFUSED_DEMAND,
        holder_faction_id=play.attacker_id,
        target_faction_id=play.defender_id,
    )
    order = DeclareWarOrder(
        faction_id=play.attacker_id,
        target_faction_id=play.defender_id,
        ground_id=ground.id,
    )
    return events + declare_war(world, scenario, order)


def _resolve_talks(
    world: WorldState, scenario: StrategyScenario, play: DiplomaticPlayState
) -> list[EventLogEntry]:
    leader = world.leaders[world.factions[play.defender_id].leader_id or ""]
    subject = world.factions[play.attacker_id].leader_id
    warmth = opinion_of(leader, subject)
    warmth += memory_warmth(leader, subject, world.clock.turn)
    is_accepted = warmth >= scenario.tuning.diplomacy.talks_refusal_warmth
    record_talks_memory(leader, subject, world.clock.turn, is_accepted)
    kind = "talks_accepted" if is_accepted else "talks_refused"
    return [diplomacy_event(kind, [play.id, play.defender_id])]


def _is_resolvable(world: WorldState, play: DiplomaticPlayState) -> bool:
    parties = (world.factions[play.attacker_id], world.factions[play.defender_id])
    return all(not faction.is_destroyed and faction.leader_id for faction in parties)


def resolve_due_plays(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    due = [
        play
        for play in sorted(world.plays, key=lambda item: item.id)
        if play.stage != "resolved" and play.due_turn <= world.clock.turn
    ]
    for play in due:
        play.stage = "resolved"
        if not _is_resolvable(world, play):
            continue
        if play.kind == "talks":
            events += _resolve_talks(world, scenario, play)
        elif demand_price_percent(world, play) <= demand_limit_percent(
            world, scenario, play
        ):
            events += _concede(world, scenario, play)
        else:
            events += _refuse(world, scenario, play)
    return events
