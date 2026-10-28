from enum import Enum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.alliances.signing import sign_alliance_card
from app.engine.coalitions.effects import coalition_shift
from app.engine.negotiation_memory import memory_warmth, record_negotiation_memory
from app.engine.opinion import opinion_of
from app.engine.outrage.demands import react_to_demand
from app.engine.outrage.effects import humiliation_shift
from app.engine.overtures.consequences import apply_overture_declined
from app.engine.peace.restoration import restore_treaty
from app.engine.peace.signing import sign_peace
from app.engine.pressure.effects import acceptance_shift, mediation_shift
from app.engine.pressure.wars import find_war
from app.engine.trait_axes import axis_totals
from app.engine.vassals.consent import has_overlord_consent
from app.engine.vassals.signing import sign_vassal_card
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_character import LeaderState
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import (
    EventCause,
    EventLogEntry,
    PendingNegotiation,
    PhaseName,
)
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.negotiation_rules import (
    DEFAULT_BASE_ACCEPT,
    DEFAULT_HAGGLE_MARGIN,
    DEFAULT_MAX_PACT_TURNS,
    DEFAULT_PACT_VALUE_PER_TURN,
)
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import AcceptanceRange, RefusedDemand, TermsResult
from strategy_contracts.terms import (
    AllianceTerm,
    NonAggressionTerm,
    PeaceTerm,
    TermsCard,
    VassalTerm,
)
from strategy_contracts.traits import TraitAxis
from strategy_contracts.vassal import ConsentAction

MAX_PACT_TURNS = DEFAULT_MAX_PACT_TURNS
NEGOTIATION_EXCHANGE_CAP = 6
PACT_VALUE_PER_TURN = DEFAULT_PACT_VALUE_PER_TURN
BASE_ACCEPT_THRESHOLD = DEFAULT_BASE_ACCEPT
HAGGLE_MARGIN = DEFAULT_HAGGLE_MARGIN
HOSTILE_AXES = (TraitAxis.AGGRESSION, TraitAxis.PRIDE)
FRIENDLY_AXES = (TraitAxis.CAUTION, TraitAxis.TRUST)
PACT_AGREED = "non_aggression_agreed"


class OfferReaction(str, Enum):
    ACCEPT = "accept"
    HAGGLE = "haggle"
    REFUSE = "refuse"


def player_faction_id(world: WorldState) -> FactionId:
    return next(key for key, faction in world.factions.items() if faction.is_player)


def _leader_of(world: WorldState, faction_id: FactionId) -> LeaderState | None:
    leader_id = world.factions[faction_id].leader_id
    return world.leaders.get(leader_id) if leader_id is not None else None


def acceptance_range(
    world: WorldState,
    scenario: StrategyScenario,
    proposer_faction_id: FactionId,
    counterpart_faction_id: FactionId,
) -> AcceptanceRange:
    """Pact value the counterpart needs to accept outright or to keep haggling."""
    rules = scenario.negotiation
    counterpart = _leader_of(world, counterpart_faction_id)
    if counterpart is None:
        return AcceptanceRange(
            accept_at=rules.base_accept,
            haggle_at=rules.base_accept - rules.haggle_margin,
        )
    totals = axis_totals(counterpart, scenario)
    hostility = sum(totals.get(axis, 0) for axis in HOSTILE_AXES)
    friendliness = sum(totals.get(axis, 0) for axis in FRIENDLY_AXES)
    proposer_leader_id = world.factions[proposer_faction_id].leader_id
    opinion = opinion_of(counterpart, proposer_leader_id)
    warmth = memory_warmth(counterpart, proposer_leader_id, world.clock.turn)
    accept_at = (
        rules.base_accept
        + rules.axis_weight * (hostility - friendliness)
        - opinion // rules.opinion_divisor
        - warmth
        - acceptance_shift(world, scenario, counterpart_faction_id)
        - mediation_shift(world, scenario, counterpart_faction_id)
        + humiliation_shift(world, scenario, counterpart_faction_id)
        + coalition_shift(world, scenario, proposer_faction_id, counterpart_faction_id)
    )
    return AcceptanceRange(
        accept_at=accept_at, haggle_at=accept_at - rules.haggle_margin
    )


def pact_value(
    duration_turns: int,
    value_per_turn: int = PACT_VALUE_PER_TURN,
    max_turns: int = MAX_PACT_TURNS,
) -> int:
    return min(duration_turns, max_turns) * value_per_turn


def react_to_pact(
    limits: AcceptanceRange,
    duration_turns: int,
    value_per_turn: int = PACT_VALUE_PER_TURN,
    max_turns: int = MAX_PACT_TURNS,
) -> OfferReaction:
    value = pact_value(duration_turns, value_per_turn, max_turns)
    if value >= limits.accept_at:
        return OfferReaction.ACCEPT
    if value >= limits.haggle_at:
        return OfferReaction.HAGGLE
    return OfferReaction.REFUSE


def active_pacts(world: WorldState) -> list[CommitmentState]:
    return [
        commitment
        for commitment in world.commitments
        if isinstance(commitment.term, NonAggressionTerm)
        and commitment.status is CommitmentStatus.ACTIVE
        and commitment.end_turn is not None
        and commitment.end_turn > world.clock.turn
    ]


def has_active_pact(world: WorldState, faction_a: str, faction_b: str) -> bool:
    pair = {faction_a, faction_b}
    return any(
        {commitment.term.faction_a, commitment.term.faction_b} == pair
        for commitment in active_pacts(world)
    )


def _next_counter(world: WorldState, kind: CounterKind) -> int:
    count = world.counters.get(kind, 0) + 1
    world.counters[kind] = count
    return count


def _pact_event(world: WorldState, term: NonAggressionTerm) -> EventLogEntry:
    return EventLogEntry(
        seq=_next_counter(world, CounterKind.EVENT_SEQ),
        turn=world.clock.turn,
        phase=PhaseName.DIPLOMACY,
        kind=PACT_AGREED,
        is_major=True,
        cause=EventCause(
            summary_key=PACT_AGREED,
            subject_ids=[term.faction_a, term.faction_b],
            inputs={"duration_turns": term.duration_turns},
        ),
    )


def apply_terms_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: str | UUID,
) -> list[EventLogEntry]:
    if not (card.is_confirmed_by_player and card.is_confirmed_by_counterpart):
        raise CampaignProgressError("terms are not confirmed", "unconfirmed_terms", 422)
    if any(isinstance(term, PeaceTerm) for term in card.terms):
        return sign_peace(world, scenario, card, scene_id)
    if any(isinstance(term, AllianceTerm) for term in card.terms):
        return sign_alliance_card(world, scenario, card, scene_id)
    if any(isinstance(term, VassalTerm) for term in card.terms):
        return sign_vassal_card(world, scenario, card, scene_id)
    events: list[EventLogEntry] = []
    for term in card.terms:
        if not isinstance(term, NonAggressionTerm):
            raise CampaignProgressError("unsupported term", "invalid_term", 422)
        number = _next_counter(world, CounterKind.COMMITMENT)
        world.commitments.append(
            CommitmentState(
                id=f"commitment_{number}",
                term=term,
                start_turn=world.clock.turn,
                end_turn=world.clock.turn + term.duration_turns,
                origin_scene_id=UUID(str(scene_id)),
            )
        )
        events.append(_pact_event(world, term))
    return events


def require_no_open_negotiation(world: WorldState) -> None:
    """Planning is frozen while a player-opened scene is pending; economy scenes keep their phase."""
    if world.progress.pending_scene_id is not None and world.progress.phase is None:
        raise CampaignProgressError("a scene is pending", "scene_pending")


def negotiation_scene_id(world: WorldState, operation_id: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{world.playthrough_id}:negotiation:{world.clock.turn}:{operation_id}",
    )


def _require_openable(world: WorldState, counterpart_faction_id: str) -> None:
    counterpart = world.factions.get(counterpart_faction_id)
    if world.progress.pending_scene_id is not None or world.progress.phase is not None:
        raise CampaignProgressError("a scene is already pending", "invalid_lifecycle")
    if counterpart is None or counterpart.is_player or counterpart.is_destroyed:
        raise CampaignProgressError("invalid counterpart", "invalid_counterpart", 422)
    if counterpart.leader_id is None or counterpart.leader_id not in world.leaders:
        raise CampaignProgressError("counterpart has no leader", "no_leader", 422)
    player = next(key for key, item in world.factions.items() if item.is_player)
    is_at_war = find_war(world, player, counterpart_faction_id) is not None
    if not is_at_war and has_active_pact(world, player, counterpart_faction_id):
        raise CampaignProgressError("a pact is already active", "pact_exists")
    if world.vassal_ruleset >= 1 and not has_overlord_consent(
        world, player, ConsentAction.PACT, counterpart_faction_id
    ):
        raise CampaignProgressError(
            "the overlord has not consented", "no_overlord_consent", 422
        )


def open_negotiation(
    world: WorldState, counterpart_faction_id: str, operation_id: str
) -> WorldState:
    _require_openable(world, counterpart_faction_id)
    opened = world.model_copy(deep=True)
    opened.progress.pending_scene_id = negotiation_scene_id(world, operation_id)
    opened.progress.negotiation_counterpart_id = counterpart_faction_id
    return opened


def _remember_outcome(
    world: WorldState, card: TermsCard | None, result: TermsResult | None
) -> None:
    counterpart_id = world.progress.negotiation_counterpart_id
    if counterpart_id is None:
        return
    counterpart = _leader_of(world, counterpart_id)
    player_leader_id = world.factions[player_faction_id(world)].leader_id
    if counterpart is None:
        return
    outcome = result or (TermsResult.AGREED if card else TermsResult.REFUSED)
    record_negotiation_memory(counterpart, player_leader_id, world.clock.turn, outcome)


def _apply_closed_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard | None,
    scene_id: UUID,
    pending: PendingNegotiation | None,
) -> list[EventLogEntry]:
    if card is None:
        return []
    overture = pending.overture if pending is not None else None
    if overture is not None and overture.truce_id is not None:
        return restore_treaty(world, scenario, overture.truce_id, card.proposer_id)
    return apply_terms_card(world, scenario, card, scene_id)


def close_negotiation(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    card: TermsCard | None,
    result: TermsResult | None = None,
    refused_demand: RefusedDemand | None = None,
) -> tuple[WorldState, list[EventLogEntry]]:
    if world.progress.pending_scene_id != scene_id:
        raise CampaignProgressError("scene unavailable", "not_found", 404)
    closed = world.model_copy(deep=True)
    pending = closed.progress.pending_negotiation
    if pending is not None:
        closed.negotiation_cooldowns[pending.trigger_id] = pending.cooldown_until_turn
    _remember_outcome(closed, card, result)
    closed.progress.pending_scene_id = None
    closed.progress.pending_negotiation = None
    closed.progress.negotiation_counterpart_id = None
    events = _apply_closed_card(closed, scenario, card, scene_id, pending)
    if card is None and pending is not None and pending.overture is not None:
        events += apply_overture_declined(
            closed,
            scenario,
            pending.overture,
            pending.initiator_faction_id,
            player_faction_id(closed),
            is_ignored=refused_demand is None,
        )
    elif card is None and refused_demand is not None:
        events += react_to_demand(
            closed,
            scenario,
            demander_id=refused_demand.terms_card.proposer_id,
            card=refused_demand.terms_card,
            tone_grade=refused_demand.tone_grade,
        )
    return closed, events
