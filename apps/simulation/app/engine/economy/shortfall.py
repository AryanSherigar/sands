from dataclasses import dataclass

from app.engine.economy import events
from app.engine.economy.credit import available_credit
from app.engine.economy.loans import take_loan
from app.engine.economy.reasons import (
    SHORTFALL_CHOICES,
    SHORTFALL_DEFAULT,
    SHORTFALL_TAKE_LOAN,
)
from app.engine.economy.state import EconomyRun
from app.engine.phases import PhaseContext, ScenePause
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scene import ChoiceOutcome, SceneType


@dataclass(frozen=True)
class ShortfallDecision:
    choice: str
    is_player_choice: bool


def _can_borrow(run: EconomyRun, faction_id: FactionId) -> bool:
    if not run.is_loans_enabled:
        return False
    return available_credit(run.world, run.tuning, faction_id) > 0


def _resolved_choice(world: WorldState, context: PhaseContext) -> str | None:
    scene_id = world.progress.pending_scene_id
    if scene_id is None or scene_id not in context.resolved_outcomes:
        return None
    outcome = context.resolved_outcomes[scene_id]
    if isinstance(outcome, ChoiceOutcome) and outcome.option_id in SHORTFALL_CHOICES:
        return outcome.option_id
    return SHORTFALL_DEFAULT


def decide_shortfall(
    run: EconomyRun, faction_id: FactionId, context: PhaseContext
) -> ShortfallDecision | ScenePause:
    if faction_id in run.declared_defaults:
        return ShortfallDecision(SHORTFALL_DEFAULT, is_player_choice=False)
    can_borrow = _can_borrow(run, faction_id)
    if not run.world.factions[faction_id].is_player:
        choice = SHORTFALL_TAKE_LOAN if can_borrow else SHORTFALL_DEFAULT
        return ShortfallDecision(choice, is_player_choice=False)
    if not can_borrow:
        return ShortfallDecision(SHORTFALL_DEFAULT, is_player_choice=False)
    choice = _resolved_choice(run.world, context)
    if choice is None:
        return ScenePause(SceneType.EVENT, (faction_id,))
    return ShortfallDecision(choice, is_player_choice=True)


def apply_shortfall_decision(
    run: EconomyRun, faction_id: FactionId, shortfall: int, decision: ShortfallDecision
) -> None:
    granted = 0
    if decision.choice == SHORTFALL_TAKE_LOAN:
        credit = available_credit(run.world, run.tuning, faction_id)
        granted = min(shortfall, credit)
        if granted > 0:
            take_loan(run, faction_id, shortfall, granted, SHORTFALL_TAKE_LOAN)
    if decision.is_player_choice:
        run.world.factions[faction_id].orders_debt += run.tuning.shortfall_order_cost
    run.events.append(
        events.shortfall_resolved(faction_id, decision.choice, shortfall, granted)
    )
