from collections.abc import Callable
from dataclasses import dataclass

from app.engine.letters.constants import LETTER_OPTION_IDS
from app.engine.negotiation_decision import Interpretation, interpret_decision
from app.engine.peace.interpretation import interpret_peace_decision
from app.engine.revolt.options import is_option_available
from app.engine.treaty.interpretation import interpret_card_decision
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_state import WorldState
from app.services.campaign_state import player_faction
from app.services.negotiation_closing import build_outcome
from strategy_contracts.judgment import JudgmentNuance, JudgmentOutcome, JudgmentVerdict
from strategy_contracts.revolt import OPTION_BY_ID
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    ChoiceOutcome,
    SceneOutcome,
    ScenePackage,
    SceneType,
)
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import TermsCard
from strategy_contracts.treaty import Verdict, WeightBand


@dataclass(frozen=True)
class SceneInterpretation:
    proposal: TermsCard | None = None
    ending: SceneOutcome | None = None
    reason: str | None = None
    verdict: Verdict | None = None
    bands: tuple[WeightBand, ...] = ()
    verdict: Verdict | None = None
    bands: tuple[WeightBand, ...] = ()


SceneInterpreter = Callable[
    [SceneDecision, ScenePackage, WorldState, StrategyScenario], SceneInterpretation
]


def _interpretation(interpreted: Interpretation) -> SceneInterpretation:
    ending = None
    if interpreted.ending is not None:
        ending = build_outcome(interpreted.ending, None)
    return SceneInterpretation(
        interpreted.proposal,
        ending,
        interpreted.reason,
        interpreted.verdict,
        interpreted.bands,
    )


def _interpret_negotiation(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    counterpart = world.leaders[package.participants[0].participant_id]
    player_id, counterpart_id = player_faction(world), counterpart.faction_id
    if world.treaty_ruleset >= 1:
        return _interpretation(
            interpret_card_decision(
                decision, package, world, scenario, player_id, counterpart_id
            )
        )
    return _interpretation(
        interpret_decision(decision, package, player_id, counterpart_id)
    )


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
    return _interpretation(interpreted)


REASON_NOT_ALLOWED = "not_allowed"


def _interpret_letter(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    if decision.action is SceneAction.CONTINUE_TALK:
        return SceneInterpretation()
    is_known_option = (
        decision.action is SceneAction.CHOOSE_OPTION
        and decision.option_id in LETTER_OPTION_IDS
    )
    if not is_known_option:
        return SceneInterpretation(reason=REASON_NOT_ALLOWED)
    return SceneInterpretation(ending=ChoiceOutcome(option_id=decision.option_id))


def _judgment_outcome(decision: SceneDecision) -> JudgmentOutcome | None:
    try:
        verdict = JudgmentVerdict(decision.option_id)
        nuance = JudgmentNuance(decision.nuance_id) if decision.nuance_id else None
        return JudgmentOutcome(verdict=verdict, nuance=nuance)
    except ValueError:
        return None


def _interpret_judgment(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    if decision.action is SceneAction.CONTINUE_TALK:
        return SceneInterpretation()
    outcome = (
        _judgment_outcome(decision)
        if decision.action is SceneAction.CHOOSE_OPTION
        else None
    )
    if outcome is None or validate_outcome_against_package(package, outcome):
        return SceneInterpretation(reason=REASON_NOT_ALLOWED)
    return SceneInterpretation(ending=outcome)


def _interpret_revolt_talk(
    decision: SceneDecision,
    package: ScenePackage,
    world: WorldState,
    scenario: StrategyScenario,
) -> SceneInterpretation:
    if decision.action is SceneAction.CONTINUE_TALK:
        return SceneInterpretation()
    pending = world.progress.pending_revolt_talk
    option = OPTION_BY_ID.get(decision.option_id or "")
    is_offerable = (
        decision.action is SceneAction.CHOOSE_OPTION
        and pending is not None
        and option is not None
        and is_option_available(world, scenario, pending, option)
    )
    if not is_offerable:
        return SceneInterpretation(reason=REASON_NOT_ALLOWED)
    return SceneInterpretation(ending=ChoiceOutcome(option_id=decision.option_id))


SCENE_INTERPRETERS: dict[SceneType, SceneInterpreter] = {
    SceneType.NEGOTIATION: _interpret_negotiation,
    SceneType.PEACE: _interpret_peace,
    SceneType.LETTER: _interpret_letter,
    SceneType.JUDGMENT: _interpret_judgment,
    SceneType.REVOLT_TALK: _interpret_revolt_talk,
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
