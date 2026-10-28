from app.engine.alliances.registry import active_alliances, alliance_term
from app.engine.diplomacy.counters import next_counter
from app.engine.pressure.wars import side_of
from app.models.world_alliance import CallToArmsState
from app.models.world_diplomacy import CommitmentState, WarSide, WarState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.alliance import AllianceType
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

CALLING_TYPE = {
    WarSide.ATTACKER: AllianceType.OFFENSIVE,
    WarSide.DEFENDER: AllianceType.DEFENSIVE,
}


def is_callable(
    world: WorldState, war: WarState, caller_id: FactionId, ally_id: FactionId
) -> bool:
    faction = world.factions.get(ally_id)
    if faction is None or faction.is_destroyed or faction.leader_id is None:
        return False
    if side_of(war, ally_id) is not None:
        return False
    return not any(
        (call.war_id, call.caller_id, call.ally_id) == (war.id, caller_id, ally_id)
        for call in world.alliance.calls
    )


def _partner(commitment: CommitmentState, faction_id: FactionId) -> FactionId:
    term = alliance_term(commitment)
    return term.faction_b if term.faction_a == faction_id else term.faction_a


def is_hostile_pair(world: WorldState, first: FactionId, second: FactionId) -> bool:
    pair = tuple(sorted((first, second)))
    return any(
        (relation.faction_a, relation.faction_b) == pair
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _new_call(
    world: WorldState,
    scenario: StrategyScenario,
    war: WarState,
    commitment: CommitmentState,
    caller_id: FactionId,
) -> CallToArmsState:
    side = side_of(war, caller_id)
    assert side is not None
    return CallToArmsState(
        id=f"call_{next_counter(world, CounterKind.CALL)}",
        alliance_id=commitment.id,
        war_id=war.id,
        caller_id=caller_id,
        ally_id=_partner(commitment, caller_id),
        side=side,
        issued_turn=world.clock.turn,
        deadline_turn=world.clock.turn + scenario.tuning.alliance.call_answer_turns,
        is_defensive=alliance_term(commitment).alliance_type is AllianceType.DEFENSIVE,
    )


def _calls_for_principal(
    world: WorldState, scenario: StrategyScenario, war: WarState, caller_id: FactionId
) -> list[CallToArmsState]:
    side = side_of(war, caller_id)
    calls: list[CallToArmsState] = []
    for commitment in active_alliances(world, caller_id):
        ally_id = _partner(commitment, caller_id)
        is_matching = alliance_term(commitment).alliance_type is CALLING_TYPE.get(side)
        is_open = is_callable(world, war, caller_id, ally_id) and not (
            is_hostile_pair(world, caller_id, ally_id)
        )
        if is_matching and is_open:
            calls.append(_new_call(world, scenario, war, commitment, caller_id))
    return calls


def issue_calls(
    world: WorldState, scenario: StrategyScenario, war: WarState
) -> list[CallToArmsState]:
    issued: list[CallToArmsState] = []
    for caller_id in (war.attacker_id, war.defender_id):
        for call in _calls_for_principal(world, scenario, war, caller_id):
            world.alliance.calls.append(call)
            issued.append(call)
    return issued
