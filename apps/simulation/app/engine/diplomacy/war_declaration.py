from app.engine.alliances.calls import issue_calls
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.reputation import shift_standing
from app.engine.peace.truces import breach_agreements
from app.engine.pressure.shocks import record_shock
from app.engine.pressure.wars import wars_of
from app.engine.vassals.levy import raise_levies
from app.engine.vassals.protection import issue_protection_calls
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import (
    GroundState,
    RelationState,
    WarGoalState,
    WarSide,
    WarState,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.diplomacy import DiplomacyTuning
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import ShockKind
from strategy_contracts.scenario import StrategyScenario


def _is_surprise(
    world: WorldState,
    tuning: DiplomacyTuning,
    attacker_id: FactionId,
    defender_id: FactionId,
) -> bool:
    earliest = world.clock.turn - tuning.warning_window_turns
    pair = {attacker_id, defender_id}
    return not any(
        {play.attacker_id, play.defender_id} == pair and play.due_turn - 1 >= earliest
        for play in world.plays
    )


def _goals_for(
    order: DeclareWarOrder, ground: GroundState | None
) -> list[WarGoalState]:
    if ground is None:
        return []
    return [
        WarGoalState(
            faction_id=order.faction_id, kind=ground.kind, region_id=ground.region_id
        )
    ]


def _principal_sides(
    world: WorldState, order: DeclareWarOrder
) -> dict[FactionId, WarSide]:
    if world.alliance_ruleset < 1:
        return {}
    return {
        order.faction_id: WarSide.ATTACKER,
        order.target_faction_id: WarSide.DEFENDER,
    }


def _set_war_relation(world: WorldState, first: FactionId, second: FactionId) -> None:
    low, high = sorted((first, second))
    for relation in world.relations:
        if (relation.faction_a, relation.faction_b) == (low, high):
            relation.status = RelationStatus.WAR
            relation.since_turn = world.clock.turn
            return
    world.relations.append(
        RelationState(
            faction_a=low,
            faction_b=high,
            status=RelationStatus.WAR,
            since_turn=world.clock.turn,
        )
    )


def _apply_ground_costs(
    world: WorldState,
    tuning: DiplomacyTuning,
    order: DeclareWarOrder,
    ground: GroundState | None,
    is_surprise: bool,
) -> list[EventLogEntry]:
    attacker = world.factions[order.faction_id]
    if ground is None:
        shift_standing(
            attacker,
            -tuning.no_ground_reputation_cost,
            -tuning.no_ground_stability_cost,
        )
        return [diplomacy_event("no_ground_penalty", [order.faction_id])]
    world.grounds = [item for item in world.grounds if item.id != ground.id]
    if is_surprise:
        shift_standing(attacker, -tuning.surprise_reputation_cost, 0)
    return [diplomacy_event("ground_spent", [order.faction_id, ground.id])]


def declare_war(
    world: WorldState, scenario: StrategyScenario, order: DeclareWarOrder
) -> list[EventLogEntry]:
    tuning = scenario.tuning.diplomacy
    ground = next((item for item in world.grounds if item.id == order.ground_id), None)
    is_surprise = _is_surprise(world, tuning, order.faction_id, order.target_faction_id)
    is_defender_busy = bool(wars_of(world, order.target_faction_id))
    events = breach_agreements(
        world, scenario, order.faction_id, order.target_faction_id
    )
    events += _apply_ground_costs(world, tuning, order, ground, is_surprise)
    war = WarState(
        id=f"war_{next_counter(world, CounterKind.WAR)}",
        attacker_id=order.faction_id,
        defender_id=order.target_faction_id,
        participant_ids=[order.faction_id, order.target_faction_id],
        started_turn=world.clock.turn,
        ground_kind=ground.kind if ground is not None else None,
        goals=_goals_for(order, ground),
        is_surprise=is_surprise,
        side_by_faction=_principal_sides(world, order),
    )
    world.wars.append(war)
    if is_defender_busy:
        record_shock(
            world, scenario, ShockKind.NEW_ENEMY, order.target_faction_id, war.id
        )
    _set_war_relation(world, order.faction_id, order.target_faction_id)
    if world.alliance_ruleset >= 1:
        issue_calls(world, scenario, war)
    if world.vassal_ruleset >= 1:
        events += raise_levies(world, scenario, war)
        issue_protection_calls(world, scenario, war)
    events.append(
        diplomacy_event(
            "war_declared",
            [war.id, order.faction_id, order.target_faction_id],
            is_major=True,
        )
    )
    return events
