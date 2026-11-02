from uuid import UUID

from app.engine.alliances.signing import sign_alliance
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.transfers import cede_region, pay_gold
from app.engine.pacts import has_active_pact, sign_pact
from app.engine.peace.signing import (
    apply_commitment,
    is_term_signable,
    release_prisoners_for_term,
    sign_peace,
)
from app.engine.pressure.wars import find_war
from app.engine.promises.signing import sign_sworn_promise
from app.engine.treaty.conditional import (
    CONDITIONAL_CLAUSE_SIGNED,
    add_conditional_commitment,
    conditional_event,
    is_condition_met,
)
from app.engine.treaty.registry import term_parties
from app.engine.vassals.signing import sign_vassalage
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    AllianceTerm,
    CedeRegionTerm,
    ConditionalMode,
    ConditionalTerm,
    HostageTerm,
    MilitaryAccessTerm,
    NonAggressionTerm,
    PayGoldTerm,
    PeaceTerm,
    ReleasePrisonersTerm,
    SwornPromiseTerm,
    Term,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
    VassalTerm,
)

TREATY_CLAUSE_SIGNED = "treaty_clause_signed"
PEACE_CARD_TERMS = (
    PeaceTerm,
    CedeRegionTerm,
    PayGoldTerm,
    TributeTerm,
    HostageTerm,
    ReleasePrisonersTerm,
    TradeDealTerm,
)
PEACETIME_ONLY_AT_PEACE = (NonAggressionTerm, TradeDealTerm, MilitaryAccessTerm)
APPLY_ORDER = (
    CedeRegionTerm,
    PayGoldTerm,
    ReleasePrisonersTerm,
    TributeTerm,
    AllianceTerm,
    VassalTerm,
    NonAggressionTerm,
    TradeDealTerm,
    MilitaryAccessTerm,
    SwornPromiseTerm,
    ConditionalTerm,
)


def _reject(code: str) -> CampaignProgressError:
    return CampaignProgressError("invalid treaty terms", code, 422)


def _signature(term: Term) -> tuple[object, ...] | None:
    if isinstance(term, PayGoldTerm):
        return None
    if isinstance(term, CedeRegionTerm):
        return (term.kind, term.region_id)
    if isinstance(term, MilitaryAccessTerm):
        return (term.kind, term.grantor_id)
    if isinstance(term, SwornPromiseTerm):
        return (term.kind, term.promisor_id, term.promise, term.subject_id)
    if isinstance(term, ConditionalTerm):
        return (
            term.kind,
            term.mode,
            term.when.template,
            term.when.region_id,
            _signature(term.inner),
        )
    return (term.kind, term_parties(term))


def _require_unique(terms: list[Term]) -> None:
    seen: set[tuple[object, ...]] = set()
    for term in terms:
        signature = _signature(term)
        if signature is None:
            continue
        if signature in seen:
            raise _reject("duplicate_term")
        seen.add(signature)


def _treasury(world: WorldState, faction_id: str) -> int:
    return world.factions[faction_id].treasury


def _check_condition_region(world: WorldState, term: ConditionalTerm) -> None:
    region_id = term.when.region_id
    if region_id is not None and region_id not in world.regions:
        raise _reject("invalid_term")


def _check_peacetime_clause(world: WorldState, term: Term, pair: set[str]) -> None:
    if not isinstance(term, APPLY_ORDER):
        raise _reject("invalid_term")
    if term_parties(term) != pair:
        raise _reject("invalid_term")
    if isinstance(term, ConditionalTerm):
        _check_condition_region(world, term)
        return
    first, second = sorted(pair)
    if isinstance(term, PEACETIME_ONLY_AT_PEACE) and find_war(world, first, second):
        raise _reject("at_war")
    if isinstance(term, NonAggressionTerm) and has_active_pact(world, first, second):
        raise CampaignProgressError("a pact is already active", "pact_exists", 409)
    if (
        isinstance(term, TributeTerm)
        and _treasury(world, term.payer_id) < term.gold_per_turn
    ):
        raise _reject("cannot_pay")
    is_transfer = isinstance(term, CedeRegionTerm | PayGoldTerm | ReleasePrisonersTerm)
    if is_transfer and not is_term_signable(world, term, pair):
        raise _reject("invalid_term")
    if isinstance(term, ReleasePrisonersTerm):
        _check_ransom_affordable(world, term)


def _check_ransom_affordable(world: WorldState, term: ReleasePrisonersTerm) -> None:
    if _treasury(world, term.recipient_id) < term.ransom_gold:
        raise _reject("cannot_pay")


def _signed(term: Term, subject_ids: list[str]) -> EventLogEntry:
    inputs = {"duration_turns": getattr(term, "duration_turns", 0)}
    return diplomacy_event(TREATY_CLAUSE_SIGNED, subject_ids, inputs, is_major=True)


def _apply_conditional(
    world: WorldState,
    scenario: StrategyScenario,
    term: ConditionalTerm,
    scene_id: UUID,
) -> list[EventLogEntry]:
    if term.mode is ConditionalMode.TRIGGER:
        commitment = add_conditional_commitment(
            world, term, scene_id, CommitmentStatus.DORMANT
        )
        return [conditional_event(CONDITIONAL_CLAUSE_SIGNED, commitment)]
    known = {item.id for item in world.commitments}
    events = _apply_clause(world, scenario, term.inner, scene_id)
    inner = next(
        (
            item
            for item in world.commitments
            if item.id not in known and item.term == term.inner
        ),
        None,
    )
    if inner is None:
        raise _reject("duplicate_term")
    if not is_condition_met(world, term):
        inner.status = CommitmentStatus.SUSPENDED
    commitment = add_conditional_commitment(
        world, term, scene_id, CommitmentStatus.ACTIVE, inner.id
    )
    return [*events, conditional_event(CONDITIONAL_CLAUSE_SIGNED, commitment)]


def sign_inner_clause(
    world: WorldState,
    scenario: StrategyScenario,
    term: Term,
    scene_id: UUID | None,
) -> list[EventLogEntry]:
    """Check and sign one clause of a trigger on the world as it is now."""
    _check_peacetime_clause(world, term, set(term_parties(term)))
    return _apply_clause(world, scenario, term, scene_id or UUID(int=0))


def _apply_clause(
    world: WorldState,
    scenario: StrategyScenario,
    term: Term,
    scene_id: UUID,
) -> list[EventLogEntry]:
    if isinstance(term, ConditionalTerm):
        return _apply_conditional(world, scenario, term, scene_id)
    if isinstance(term, NonAggressionTerm):
        return [sign_pact(world, term, scene_id)]
    if isinstance(term, SwornPromiseTerm):
        return sign_sworn_promise(world, term, scene_id)
    if isinstance(term, AllianceTerm):
        return sign_alliance(world, scenario, term, scene_id)
    if isinstance(term, VassalTerm):
        return sign_vassalage(world, scenario, term, scene_id)
    if isinstance(term, CedeRegionTerm):
        cede_region(world, scenario, term)
    elif isinstance(term, PayGoldTerm):
        pay_gold(world, term)
    elif isinstance(term, ReleasePrisonersTerm):
        release_prisoners_for_term(world, term)
    else:
        apply_commitment(world, term, scene_id)
    return [_signed(term, sorted(term_parties(term)))]


def _rank(term: Term) -> int:
    return next(
        (index for index, kind in enumerate(APPLY_ORDER) if isinstance(term, kind)),
        len(APPLY_ORDER),
    )


def _split_peace(card: TermsCard) -> tuple[TermsCard | None, list[Term]]:
    if not any(isinstance(term, PeaceTerm) for term in card.terms):
        return None, list(card.terms)
    peace_terms = [term for term in card.terms if isinstance(term, PEACE_CARD_TERMS)]
    rest = [term for term in card.terms if not isinstance(term, PEACE_CARD_TERMS)]
    return card.model_copy(update={"terms": peace_terms}), rest


def _apply_all(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: UUID,
) -> list[EventLogEntry]:
    _require_unique(card.terms)
    peace_card, rest = _split_peace(card)
    events: list[EventLogEntry] = []
    if peace_card is not None:
        events += sign_peace(world, scenario, peace_card, scene_id)
    pair = {card.proposer_id, card.counterpart_id}
    for term in sorted(rest, key=_rank):
        _check_peacetime_clause(world, term, pair)
        events += _apply_clause(world, scenario, term, scene_id)
    return events


def apply_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: str | UUID,
) -> list[EventLogEntry]:
    """Sign every clause of a confirmed card, or none: the world changes only if all succeed."""
    working = world.model_copy(deep=True)
    events = _apply_all(working, scenario, card, UUID(str(scene_id)))
    world.__dict__.update(working.__dict__)
    return events


def validate_card(
    world: WorldState, scenario: StrategyScenario, card: TermsCard
) -> None:
    """Raise CampaignProgressError when the card could not be signed right now."""
    trial = world.model_copy(deep=True)
    _apply_all(trial, scenario, card, UUID(int=0))
