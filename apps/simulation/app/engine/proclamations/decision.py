from app.engine.endings import require_game_not_ended
from app.engine.proclamations.constants import PROCLAMATION_MANDATE_COST
from app.engine.proclamations.lifecycle import apply_proclamation_enactment
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.replay import ProclamationDecisionReplayInput
from app.models.world_events import (
    EventCause,
    EventLogEntry,
    PhaseName,
    StateChange,
)
from app.models.world_faction import FactionState
from app.models.world_state import CounterKind, WorldState

PROCLAMATION_ENACTED = "proclamation_enacted"
VERDICT_COMPROMISE = "compromise"


def player_faction_state(world: WorldState) -> FactionState | None:
    return next(
        (faction for faction in world.factions.values() if faction.is_player), None
    )


def require_proclamation_allowed(
    world: WorldState, is_rescinding_previous: bool
) -> FactionState:
    require_game_not_ended(world)
    player = player_faction_state(world)
    if player is None or player.orders_remaining < PROCLAMATION_MANDATE_COST:
        raise CampaignProgressError(
            "Insufficient Royal Mandates (2 required)",
            "insufficient_mandates",
            400,
        )
    has_active = (
        world.active_proclamation is not None
        and world.active_proclamation.remaining_turns > 0
    )
    if has_active and not is_rescinding_previous:
        raise CampaignProgressError(
            "An active proclamation is already in effect. Must rescind previous.",
            "active_proclamation_conflict",
            400,
        )
    return player


def _require_recognized(replay_input: ProclamationDecisionReplayInput) -> None:
    draft = replay_input.draft
    if not draft.is_recognized or draft.domain is None or draft.burden is None:
        raise CampaignProgressError(
            "The proclamation was not understood by the council",
            "unrecognized_proclamation",
            422,
        )


def _enacted_event(
    world: WorldState, domain: str, mandates: int, immediate: dict[str, int]
) -> EventLogEntry:
    sequence = world.counters.get(CounterKind.EVENT_SEQ, 0) + 1
    world.counters[CounterKind.EVENT_SEQ] = sequence
    return EventLogEntry(
        seq=sequence,
        turn=world.clock.turn,
        phase=PhaseName.ORDERS,
        kind=PROCLAMATION_ENACTED,
        is_major=True,
        cause=EventCause(
            summary_key=PROCLAMATION_ENACTED,
            subject_ids=[domain],
            inputs=dict(immediate),
        ),
        changes=[StateChange(path="factions.player.orders_remaining", after=mandates)],
    )


def enact_proclamation_decision(
    world: WorldState, replay_input: ProclamationDecisionReplayInput
) -> EventLogEntry:
    """Charge the mandates and enact the edict on the world, in place."""
    _require_recognized(replay_input)
    player = require_proclamation_allowed(world, replay_input.is_rescinding_previous)
    player.orders_remaining -= PROCLAMATION_MANDATE_COST
    active = apply_proclamation_enactment(
        world,
        replay_input.draft,
        is_rescinding=replay_input.is_rescinding_previous,
        is_compromise=replay_input.verdict == VERDICT_COMPROMISE,
    )
    return _enacted_event(
        world, active.domain.value, player.orders_remaining, active.immediate_deltas
    )
