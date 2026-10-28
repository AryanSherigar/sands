from dataclasses import dataclass

from app.models.world_internal import (
    UprisingArchetype,
    UprisingResponse,
    UprisingState,
)
from strategy_contracts.events import EffectKind
from strategy_contracts.scenario import InternalTuning


@dataclass(frozen=True)
class ResponsePreview:
    effects: tuple[tuple[EffectKind, int], ...]
    notes: tuple[str, ...]


def preview_response(
    response: UprisingResponse, uprising: UprisingState, tuning: InternalTuning
) -> ResponsePreview:
    """What answering would do, from the same numbers resolution applies."""
    if response is UprisingResponse.CONCESSIONS:
        return _concessions(uprising, tuning)
    if response is UprisingResponse.RESTORE_ORDER:
        return _restore_order(tuning)
    return ResponsePreview(
        effects=((EffectKind.REGION_UNREST, -tuning.negotiate_unrest_reduction),),
        notes=("The crowd is heard, but nothing is promised.",),
    )


def _concessions(uprising: UprisingState, tuning: InternalTuning) -> ResponsePreview:
    cost = tuning.concessions_reputation_cost
    if uprising.archetype is UprisingArchetype.REBELLION:
        cost *= tuning.rebellion_concessions_cost_multiplier
    return ResponsePreview(
        effects=(
            (EffectKind.REGION_UNREST, -tuning.concessions_unrest_reduction),
            (EffectKind.STABILITY, tuning.concessions_stability_gain),
            (EffectKind.REPUTATION, -cost),
        ),
        notes=(
            f"Other restless provinces grow bolder (+{tuning.precedent_unrest} unrest).",
        ),
    )


def _restore_order(tuning: InternalTuning) -> ResponsePreview:
    return ResponsePreview(
        effects=(
            (EffectKind.REGION_UNREST, -tuning.restore_order_unrest_reduction),
            (EffectKind.STABILITY, -tuning.restore_order_stability_loss),
        ),
        notes=(
            f"A grudge lingers for {tuning.restore_order_grudge_turns} turns "
            f"(+{tuning.restore_order_grudge_unrest} unrest each turn).",
        ),
    )
