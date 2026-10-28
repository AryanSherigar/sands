from dataclasses import dataclass

from app.engine.ai.aims import refresh_aim
from app.engine.ai.candidates import ScoredCandidate
from app.engine.ai.catalog import generate_candidates, legal_candidates
from app.engine.ai.events import stamp_ai_event
from app.engine.ai.rescoring import rescore
from app.engine.ai.scoring import score_candidate
from app.engine.ai.selection import select_orders
from app.engine.commands.application import CommandAcceptance, accept_command
from app.engine.rng import derive_rng
from app.exceptions.command_exceptions import CommandError
from app.models.world_events import EventCause, EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

PLANNING_STREAM = "ai_planning"
AIM_STREAM = "ai_aims"
AIMS_RULESET = 2
PLANNED_KIND = "ai_order_planned"
REJECTED_KIND = "ai_order_rejected"


@dataclass(frozen=True)
class AiPlan:
    world: WorldState
    events: list[EventLogEntry]


def plan_ai_orders(world: WorldState, scenario: StrategyScenario) -> AiPlan:
    planned = world.model_copy(deep=True)
    events: list[EventLogEntry] = []
    for faction_id in _planning_faction_ids(planned):
        planned, faction_events = plan_faction_orders(planned, scenario, faction_id)
        events.extend(faction_events)
    return AiPlan(planned, events)


def _planning_faction_ids(world: WorldState) -> list[FactionId]:
    return sorted(
        faction_id
        for faction_id, faction in world.factions.items()
        if not faction.is_player
        and not faction.is_destroyed
        and faction.leader_id is not None
    )


def _pick_orders(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[ScoredCandidate]:
    candidates = generate_candidates(world, scenario, faction_id)
    legal = legal_candidates(world, scenario, faction_id, candidates)
    scored = [score_candidate(world, scenario, faction_id, item) for item in legal]
    scored = rescore(world, scenario, faction_id, scored)
    rng = derive_rng(world.rng.seed, world.clock.turn, PLANNING_STREAM, faction_id)
    return select_orders(
        scored,
        budget=world.factions[faction_id].orders_remaining,
        tuning=scenario.tuning.ai,
        world=world,
        scenario=scenario,
        rng=rng,
    )


def _refresh_aim_events(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[EventLogEntry]:
    if world.ai_ruleset < AIMS_RULESET:
        return []
    rng = derive_rng(world.rng.seed, world.clock.turn, AIM_STREAM, faction_id)
    event = refresh_aim(world, scenario, faction_id, rng)
    return [] if event is None else [event]


def plan_faction_orders(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> tuple[WorldState, list[EventLogEntry]]:
    events = _refresh_aim_events(world, scenario, faction_id)
    picks = _pick_orders(world, scenario, faction_id)
    for index, pick in enumerate(picks):
        world, new_events = _accept_pick(world, scenario, faction_id, index, pick)
        events.extend(new_events)
    return world, events


def _accept_pick(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    index: int,
    pick: ScoredCandidate,
) -> tuple[WorldState, list[EventLogEntry]]:
    identity = f"ai:{faction_id}:{world.clock.turn}:{index}"
    try:
        acceptance = _accept_order(world, scenario, faction_id, identity, pick)
    except CommandError as error:
        cause = EventCause(
            summary_key=f"ai_rejected_{error.code}", subject_ids=[faction_id]
        )
        return world, [stamp_ai_event(world, REJECTED_KIND, cause)]
    accepted = acceptance.world
    reason = stamp_ai_event(accepted, PLANNED_KIND, _planned_cause(faction_id, pick))
    return accepted, [*acceptance.events, reason]


def _accept_order(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    identity: str,
    pick: ScoredCandidate,
) -> CommandAcceptance:
    return accept_command(
        world,
        scenario,
        pick.candidate.order,
        command_id=identity,
        operation_id=identity,
        actor_id=f"npc:{faction_id}",
        faction_id=faction_id,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )


def _planned_cause(faction_id: FactionId, pick: ScoredCandidate) -> EventCause:
    suffix = "_aim" if pick.aim_score > 0 else ""
    return EventCause(
        summary_key=f"ai_{pick.candidate.category.value}{suffix}",
        subject_ids=[faction_id],
        inputs={
            "score": pick.score,
            "trait_score": pick.trait_score,
            "stance_score": pick.stance_score,
            "aim_score": pick.aim_score,
            "adjustment": pick.adjustment,
        },
    )
