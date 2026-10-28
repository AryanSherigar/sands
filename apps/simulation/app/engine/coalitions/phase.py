from app.engine.coalitions.membership import would_join
from app.engine.coalitions.registry import coalition_against
from app.engine.coalitions.threat import compute_threat
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.movement.map_index import MapIndex, build_map_index
from app.engine.opinion import shift_opinion
from app.models.world_coalition import CoalitionState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

COALITION_FORMED = "coalition_formed"
COALITION_JOINED = "coalition_joined"
COALITION_RENEWED = "coalition_renewed"
COALITION_ENDED_THREAT = "coalition_ended_threat"
COALITION_ENDED_CONCEDED = "coalition_ended_conceded"
COALITION_ENDED_SPLIT = "coalition_ended_split"
COALITION_ENDED_EXPIRED = "coalition_ended_expired"
COALITION_ENDED_FALLEN = "coalition_ended_fallen"
OPINION_CAUSE_PREFIX = "coalition:"


def _event(
    kind: str, coalition: CoalitionState, *, is_major: bool = False
) -> EventLogEntry:
    return diplomacy_event(
        kind,
        [coalition.id, coalition.target_id, *coalition.member_ids],
        {"members": len(coalition.member_ids)},
        phase=PhaseName.TIME,
        is_major=is_major,
    )


def _enlist(
    world: WorldState,
    scenario: StrategyScenario,
    coalition: CoalitionState,
    member_id: FactionId,
) -> None:
    coalition.member_ids = sorted([*coalition.member_ids, member_id])
    shift_opinion(
        world,
        member_id,
        coalition.target_id,
        f"{OPINION_CAUSE_PREFIX}{coalition.id}",
        -scenario.tuning.coalition.member_opinion_penalty,
        0,
    )
    grant_ground(
        world,
        scenario,
        kind=GroundKind.BROKEN_PROMISE,
        holder_faction_id=member_id,
        target_faction_id=coalition.target_id,
    )


def _lift_opinion_penalties(world: WorldState, coalition: CoalitionState) -> None:
    cause = f"{OPINION_CAUSE_PREFIX}{coalition.id}"
    for leader in world.leaders.values():
        for opinion in leader.opinions.values():
            opinion.reasons = [item for item in opinion.reasons if item.cause != cause]


def _would_be_members(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    target_id: FactionId,
    threat: int,
) -> list[FactionId]:
    willing = [
        member_id
        for member_id in sorted(world.factions)
        if would_join(world, scenario, index, member_id, target_id, threat)
    ]
    return _without_warring_pairs(world, willing)


def _without_warring_pairs(
    world: WorldState, candidates: list[FactionId]
) -> list[FactionId]:
    accepted: list[FactionId] = []
    for member_id in candidates:
        if not any(_are_at_war(world, member_id, other) for other in accepted):
            accepted.append(member_id)
    return accepted


def _are_at_war(world: WorldState, left_id: FactionId, right_id: FactionId) -> bool:
    return any(
        {war.attacker_id, war.defender_id} == {left_id, right_id} for war in world.wars
    )


def _form(
    world: WorldState, scenario: StrategyScenario, target_id: FactionId
) -> CoalitionState:
    tuning = scenario.tuning.coalition
    return CoalitionState(
        id=f"coalition_{next_counter(world, CounterKind.COALITION)}",
        target_id=target_id,
        formed_turn=world.clock.turn,
        expires_turn=world.clock.turn + tuning.duration_turns,
    )


def _recruit(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    target_id: FactionId,
    threat: int,
) -> list[EventLogEntry]:
    candidates = _would_be_members(world, scenario, index, target_id, threat)
    existing = coalition_against(world, target_id)
    if existing is not None:
        for member_id in candidates:
            _enlist(world, scenario, existing, member_id)
        return [_event(COALITION_JOINED, existing)] if candidates else []
    if len(candidates) < scenario.tuning.coalition.min_members:
        return []
    coalition = _form(world, scenario, target_id)
    for member_id in candidates:
        _enlist(world, scenario, coalition, member_id)
    world.coalition.coalitions.append(coalition)
    return [_event(COALITION_FORMED, coalition, is_major=True)]


def _is_split(world: WorldState, coalition: CoalitionState) -> bool:
    members = set(coalition.member_ids)
    return any(
        war.attacker_id in members and war.defender_id in members for war in world.wars
    )


def _end_reason(
    world: WorldState,
    scenario: StrategyScenario,
    coalition: CoalitionState,
    threat: int,
) -> str | None:
    tuning = scenario.tuning.coalition
    if world.factions[coalition.target_id].is_destroyed:
        return COALITION_ENDED_FALLEN
    if _is_split(world, coalition):
        return COALITION_ENDED_SPLIT
    if len(coalition.member_ids) < tuning.min_members:
        return COALITION_ENDED_CONCEDED
    if threat < tuning.end_threat:
        return COALITION_ENDED_THREAT
    return None


def _prune_members(world: WorldState, coalition: CoalitionState) -> None:
    coalition.member_ids = [
        member_id
        for member_id in coalition.member_ids
        if not world.factions[member_id].is_destroyed
    ]


def _review(
    world: WorldState,
    scenario: StrategyScenario,
    coalition: CoalitionState,
    threat: int,
) -> list[EventLogEntry]:
    _prune_members(world, coalition)
    reason = _end_reason(world, scenario, coalition, threat)
    is_expired = world.clock.turn >= coalition.expires_turn
    if reason is None and not is_expired:
        return []
    if reason is None:
        coalition.expires_turn += scenario.tuning.coalition.duration_turns
        return [_event(COALITION_RENEWED, coalition)]
    _lift_opinion_penalties(world, coalition)
    world.coalition.coalitions.remove(coalition)
    return [_event(reason, coalition, is_major=True)]


def tick_coalitions(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    if world.coalition_ruleset < 1:
        return []
    index = build_map_index(scenario.map)
    threats = {
        faction_id: compute_threat(world, scenario, faction_id).value
        for faction_id in sorted(world.factions)
    }
    events: list[EventLogEntry] = []
    for coalition in list(world.coalition.coalitions):
        events += _review(world, scenario, coalition, threats[coalition.target_id])
    for target_id, threat in threats.items():
        if not world.factions[target_id].is_destroyed:
            events += _recruit(world, scenario, index, target_id, threat)
    return events
