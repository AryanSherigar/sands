from uuid import uuid4

from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.pressure.wars import side_of
from app.engine.vassals.cleanup import clear_vassalage_state
from app.engine.vassals.registry import vassal_term
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import (
    CommitmentState,
    CommitmentStatus,
    WarSide,
    WarState,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.scenario import StrategyScenario

VASSAL_REBELLED = "vassal_rebelled"
VASSAL_INDEPENDENT = "vassal_independent"
REBEL_REBOUND = "rebel_rebound"


def start_independence_war(
    world: WorldState, scenario: StrategyScenario, commitment: CommitmentState
) -> list[EventLogEntry]:
    term = vassal_term(commitment)
    commitment.status = CommitmentStatus.BREACHED
    clear_vassalage_state(world, commitment.id)
    ground = grant_ground(
        world,
        scenario,
        kind=GroundKind.INDEPENDENCE,
        holder_faction_id=term.vassal_id,
        target_faction_id=term.overlord_id,
    )
    events = declare_war(
        world,
        scenario,
        DeclareWarOrder(
            faction_id=term.vassal_id,
            target_faction_id=term.overlord_id,
            ground_id=ground.id,
        ),
    )
    war = world.wars[-1]
    world.vassal.independence_wars[war.id] = commitment.id
    events.append(
        diplomacy_event(
            VASSAL_REBELLED, [term.vassal_id, term.overlord_id], is_major=True
        )
    )
    return events


def _loser_is_rebel(war: WarState, rebel_id: str) -> bool:
    if war.war_score_attacker == war.war_score_defender:
        return False
    losing_side = (
        WarSide.DEFENDER
        if war.war_score_attacker > war.war_score_defender
        else WarSide.ATTACKER
    )
    return side_of(war, rebel_id) is losing_side


def _rebind(world: WorldState, commitment: CommitmentState) -> CommitmentState:
    term = vassal_term(commitment)
    end_turn = world.clock.turn + term.duration_turns if term.duration_turns else None
    bound = CommitmentState(
        id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
        term=term,
        start_turn=world.clock.turn,
        end_turn=end_turn,
        origin_scene_id=uuid4(),
    )
    world.commitments.append(bound)
    return bound


def settle_independence(world: WorldState, war: WarState) -> list[EventLogEntry]:
    commitment_id = world.vassal.independence_wars.pop(war.id, None)
    if commitment_id is None:
        return []
    commitment = next(item for item in world.commitments if item.id == commitment_id)
    term = vassal_term(commitment)
    if _loser_is_rebel(war, term.vassal_id):
        _rebind(world, commitment)
        return [diplomacy_event(REBEL_REBOUND, [term.vassal_id, term.overlord_id])]
    return [diplomacy_event(VASSAL_INDEPENDENT, [term.vassal_id, term.overlord_id])]
