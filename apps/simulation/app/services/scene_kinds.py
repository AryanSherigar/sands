from collections.abc import Callable
from dataclasses import dataclass

from app.engine.negotiation_decision import interpret_decision
from app.engine.peace.interpretation import interpret_peace_decision
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_state import WorldState
from app.services.campaign_state import player_faction
from app.services.negotiation_closing import build_outcome
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome, ScenePackage, SceneType
from strategy_contracts.scene_exchange import SceneDecision
from strategy_contracts.terms import TermsCard


@dataclass(frozen=True)
class SceneInterpretation:
    proposal: TermsCard | None = None
    ending: SceneOutcome | None = None
    reason: str | None = None


SceneInterpreter = Callable[
    [SceneDecision, ScenePackage, WorldState, StrategyScenario], SceneInterpretation
]


def _interpret_negotiation(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    counterpart = world.leaders[package.participants[0].participant_id]
    interpreted = interpret_decision(
        decision, package, player_faction(world), counterpart.faction_id
    )
    ending = None
    if interpreted.ending is not None:
        ending = build_outcome(interpreted.ending, None)
    return SceneInterpretation(interpreted.proposal, ending, interpreted.reason)


def _interpret_peace(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    counterpart = world.leaders[package.participants[0].participant_id]
    interpreted = interpret_peace_decision(
        decision,
        package,
        world,
        scenario,
        player_faction(world),
        counterpart.faction_id,
    )
    ending = None
    if interpreted.ending is not None:
        ending = build_outcome(interpreted.ending, None)
    return SceneInterpretation(interpreted.proposal, ending, interpreted.reason)


SCENE_INTERPRETERS: dict[SceneType, SceneInterpreter] = {
    SceneType.NEGOTIATION: _interpret_negotiation,
    SceneType.PEACE: _interpret_peace,
}


def interpret_scene_decision(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    """Bound a model's proposed step by the scene's hidden limits and allowed outcomes."""
    interpreter = SCENE_INTERPRETERS.get(package.scene_type)
    if interpreter is None:
        raise CampaignProgressError("unsupported scene type", "invalid_lifecycle")
    return interpreter(decision, package, world, scenario)
