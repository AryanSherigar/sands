from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from app.engine.campaign import advance_campaign, begin_campaign, resume_campaign
from app.engine.commands.application import accept_command
from app.engine.commands.cancellation import cancel_command
from app.engine.hashing import world_hash
from app.engine.negotiation import close_negotiation, open_negotiation
from app.engine.scene_closing import close_scene
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.replay import (
    AcceptCommandReplayInput,
    AdvanceCampaignReplayInput,
    BeginCampaignReplayInput,
    BeginNegotiationReplayInput,
    CancelCommandReplayInput,
    ReplayStep,
    ResolveNegotiationReplayInput,
    ResolveSceneReplayInput,
    ResumeEconomyReplayInput,
    ordered_replay_steps,
)
from app.models.stance import StanceChoice
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ChoiceOutcome


@dataclass(frozen=True)
class ReplayResult:
    world: WorldState
    world_hash: str
    step_count: int


def replay_history(
    initial_world: WorldState, scenario: StrategyScenario, steps: list[ReplayStep]
) -> ReplayResult:
    world = initial_world.model_copy(deep=True)
    ordered = ordered_replay_steps(steps)
    for step in ordered:
        _require_hash(step, world_hash(world), step.before_hash)
        world = _apply_step(world, scenario, step)
        _require_hash(step, world_hash(world), step.after_hash)
    return ReplayResult(world, world_hash(world), len(ordered))


def _apply_step(
    world: WorldState, scenario: StrategyScenario, step: ReplayStep
) -> WorldState:
    replay_input = step.input
    if isinstance(replay_input, AcceptCommandReplayInput):
        return _accept_command(world, scenario, replay_input)
    if isinstance(replay_input, CancelCommandReplayInput):
        return cancel_command(
            world,
            scenario,
            replay_input.command_id,
            faction_id=_player_faction(world),
            expected_turn=replay_input.guard.expected_turn,
        )
    if isinstance(replay_input, BeginCampaignReplayInput):
        return begin_campaign(
            world, scenario, recorded_stances=_recorded_stances(replay_input.stances)
        ).world
    if isinstance(replay_input, AdvanceCampaignReplayInput):
        return advance_campaign(
            world,
            scenario,
            expected_turn=replay_input.guard.expected_turn,
            expected_wave=replay_input.guard.expected_wave,
            recorded_intents={intent.id: intent for intent in replay_input.intents},
            recorded_stances=_recorded_stances(replay_input.stances),
        ).result.world
    if isinstance(replay_input, ResumeEconomyReplayInput):
        outcome = ChoiceOutcome(option_id=replay_input.choice)
        return resume_campaign(
            world,
            scenario,
            {replay_input.scene_id: outcome},
            recorded_stances=_recorded_stances(replay_input.stances),
        ).world
    if isinstance(
        replay_input, BeginNegotiationReplayInput | ResolveNegotiationReplayInput
    ):
        return _apply_negotiation_step(world, scenario, replay_input)
    if isinstance(replay_input, ResolveSceneReplayInput):
        return close_scene(
            world,
            scenario,
            replay_input.scene_type,
            replay_input.scene_id,
            replay_input.outcome,
        )[0]
    raise ReplayMismatchError(
        step.sequence, "known replay input", "unknown replay input"
    )


def _recorded_stances(stances: list[StanceChoice]) -> dict[str, StanceChoice]:
    return {choice.leader_id: choice for choice in stances}


def _apply_negotiation_step(
    world: WorldState,
    scenario: StrategyScenario,
    replay_input: BeginNegotiationReplayInput | ResolveNegotiationReplayInput,
) -> WorldState:
    if isinstance(replay_input, BeginNegotiationReplayInput):
        return open_negotiation(
            world, replay_input.counterpart_faction_id, replay_input.guard.operation_id
        )
    return close_negotiation(
        world,
        scenario,
        replay_input.scene_id,
        replay_input.terms_card,
        replay_input.result,
        replay_input.refused_demand,
    )[0]


def _accept_command(
    world: WorldState,
    scenario: StrategyScenario,
    replay_input: AcceptCommandReplayInput,
) -> WorldState:
    identity = uuid5(
        NAMESPACE_URL,
        f"{world.playthrough_id}:{replay_input.actor_id}:{replay_input.guard.operation_id}",
    )
    return accept_command(
        world,
        scenario,
        replay_input.command,
        command_id=str(identity),
        operation_id=replay_input.guard.operation_id,
        actor_id=replay_input.actor_id,
        faction_id=_player_faction(world),
        expected_turn=replay_input.guard.expected_turn,
        expected_wave=replay_input.guard.expected_wave,
    ).world


def _player_faction(world: WorldState) -> str:
    return next(key for key, faction in world.factions.items() if faction.is_player)


def _require_hash(step: ReplayStep, actual: str, expected: str) -> None:
    if actual != expected:
        raise ReplayMismatchError(step.sequence, expected, actual)
