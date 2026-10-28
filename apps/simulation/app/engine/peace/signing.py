from uuid import UUID

from app.engine.alliances.separate_peace import breach_separate_peace
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.prisoners import find_prisoner, free_prisoner
from app.engine.diplomacy.transfers import cede_region, pay_gold
from app.engine.peace.breach import card_harshness, ceded_regions
from app.engine.peace.hostages import hold_hostage
from app.engine.peace.parties import (
    check_parties,
    open_pairs,
    pair_is_at_war,
    remaining_pairs,
    signing_parties,
)
from app.engine.peace.pricing import can_afford
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import find_war, side_of, side_score
from app.engine.vassals.independence import settle_independence
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import (
    CommitmentState,
    TruceState,
    WarSide,
    WarState,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    CedeRegionTerm,
    HostageTerm,
    PayGoldTerm,
    PeaceTerm,
    ReleasePrisonersTerm,
    Term,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
)

PEACE_SIGNED = "peace_signed"


def is_white_peace_eligible(
    world: WorldState, scenario: StrategyScenario, war: WarState
) -> bool:
    tuning = scenario.tuning.peace
    for faction_id in (war.attacker_id, war.defender_id):
        if side_score(war, faction_id) > tuning.white_peace_score_ceiling:
            return False
        strain = compute_strain(world, scenario, faction_id).value
        if strain < tuning.white_peace_min_strain:
            return False
    return True


def _reject(code: str) -> CampaignProgressError:
    return CampaignProgressError("invalid peace terms", code, 422)


def _peace_term(card: TermsCard) -> PeaceTerm:
    peace = [term for term in card.terms if isinstance(term, PeaceTerm)]
    if len(peace) != 1:
        raise _reject("invalid_term")
    return peace[0]


def _check_cession(world: WorldState, term: CedeRegionTerm, pair: set[str]) -> None:
    region = world.regions.get(term.region_id)
    is_in_pair = {term.from_faction_id, term.to_faction_id} == pair
    if region is None or region.owner_id != term.from_faction_id or not is_in_pair:
        raise _reject("invalid_term")


def _check_release(
    world: WorldState, term: ReleasePrisonersTerm, pair: set[str]
) -> None:
    if {term.holder_id, term.recipient_id} != pair:
        raise _reject("invalid_term")
    for prisoner_id in term.prisoner_ids:
        prisoner = find_prisoner(world, prisoner_id)
        if prisoner is None or (prisoner.held_by_id, prisoner.origin_faction_id) != (
            term.holder_id,
            term.recipient_id,
        ):
            raise _reject("invalid_term")


def _check_payment(world: WorldState, term: PayGoldTerm, pair: set[str]) -> None:
    if {term.payer_id, term.payee_id} != pair:
        raise _reject("invalid_term")
    if world.factions[term.payer_id].treasury < term.amount:
        raise _reject("cannot_pay")


def _check_hostage(world: WorldState, term: HostageTerm, pair: set[str]) -> None:
    leader = world.leaders.get(term.leader_id)
    is_in_pair = {term.giver_id, term.holder_id} == pair
    if leader is None or leader.faction_id != term.giver_id or not is_in_pair:
        raise _reject("invalid_term")


def _check_term(world: WorldState, term: Term, pair: set[str]) -> None:
    if isinstance(term, ReleasePrisonersTerm):
        _check_release(world, term, pair)
    elif isinstance(term, CedeRegionTerm):
        _check_cession(world, term, pair)
    elif isinstance(term, PayGoldTerm):
        _check_payment(world, term, pair)
    elif isinstance(term, HostageTerm):
        _check_hostage(world, term, pair)
    elif not isinstance(term, PeaceTerm | TributeTerm | TradeDealTerm):
        raise _reject("invalid_term")


def _check_guarantors(world: WorldState, peace: PeaceTerm) -> None:
    pair = {peace.faction_a, peace.faction_b}
    for guarantor_id in peace.guarantor_ids:
        faction = world.factions.get(guarantor_id)
        if faction is None or faction.is_destroyed or guarantor_id in pair:
            raise _reject("invalid_term")


def _validate(
    world: WorldState, scenario: StrategyScenario, card: TermsCard, war: WarState
) -> PeaceTerm:
    peace = _peace_term(card)
    pair = {peace.faction_a, peace.faction_b}
    for term in card.terms:
        _check_term(world, term, pair)
    _check_guarantors(world, peace)
    if not can_afford(world, scenario, card, card.proposer_id, war):
        raise _reject("exceeds_score")
    if peace.is_white_peace and not _is_white_peace_card(world, scenario, card, war):
        raise _reject("not_white_peace")
    return peace


def _is_white_peace_card(
    world: WorldState, scenario: StrategyScenario, card: TermsCard, war: WarState
) -> bool:
    is_bare = len(card.terms) == 1
    return is_bare and is_white_peace_eligible(world, scenario, war)


def _apply_commitment(world: WorldState, term: Term, scene_id: UUID | str) -> None:
    world.commitments.append(
        CommitmentState(
            id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
            term=term,
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + getattr(term, "duration_turns", 0),
            origin_scene_id=UUID(str(scene_id)),
        )
    )


def _release_prisoners(world: WorldState, term: ReleasePrisonersTerm) -> None:
    for prisoner_id in term.prisoner_ids:
        prisoner = find_prisoner(world, prisoner_id)
        if prisoner is not None:
            free_prisoner(world, prisoner)
    if term.ransom_gold:
        pay_gold(
            world,
            PayGoldTerm(
                payer_id=term.recipient_id,
                payee_id=term.holder_id,
                amount=term.ransom_gold,
            ),
        )


def _apply_term(
    world: WorldState,
    scenario: StrategyScenario,
    term: Term,
    scene_id: UUID | str,
    truce: TruceState,
) -> None:
    if isinstance(term, HostageTerm):
        hold_hostage(world, term, truce.id)
    elif isinstance(term, ReleasePrisonersTerm):
        _release_prisoners(world, term)
    elif isinstance(term, CedeRegionTerm):
        cede_region(world, scenario, term)
    elif isinstance(term, PayGoldTerm):
        pay_gold(world, term)
    elif isinstance(term, TributeTerm | TradeDealTerm):
        _apply_commitment(world, term, scene_id)


def _is_fragile(scenario: StrategyScenario, peace: PeaceTerm) -> bool:
    tuning = scenario.tuning.peace
    order = list(PeaceTier)
    is_long = order.index(peace.tier) >= order.index(tuning.guarantor_required_from)
    return is_long and not peace.guarantor_ids


def _loser_of(war: WarState, pair: tuple[FactionId, FactionId]) -> FactionId | None:
    if war.war_score_attacker == war.war_score_defender:
        return None
    losing_side = (
        WarSide.DEFENDER
        if war.war_score_attacker > war.war_score_defender
        else WarSide.ATTACKER
    )
    return next((item for item in pair if side_of(war, item) is losing_side), None)


def _pair_harshness(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    loser_id: FactionId | None,
    is_principal_pair: bool,
) -> int:
    if loser_id is None or not is_principal_pair:
        return 0
    return card_harshness(world, scenario, card, loser_id)


def _create_truce(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    peace: PeaceTerm,
    war: WarState,
    pair: tuple[FactionId, FactionId],
) -> TruceState:
    first, second = pair
    is_principal_pair = {first, second} == {peace.faction_a, peace.faction_b}
    loser_id = _loser_of(war, pair)
    length = scenario.tuning.peace.tier_turns[peace.tier]
    expires = world.clock.turn + length if length else 0
    leaders = [world.factions[faction_id].leader_id for faction_id in pair]
    truce = TruceState(
        id=f"truce_{next_counter(world, CounterKind.TRUCE)}",
        faction_a=first,
        faction_b=second,
        expires_turn=expires,
        signed_turn=world.clock.turn,
        tier=peace.tier,
        guarantor_ids=sorted(peace.guarantor_ids),
        signatory_leader_ids=[leader for leader in leaders if leader is not None],
        is_fragile=_is_fragile(scenario, peace),
        origin_war_id=war.id,
        loser_id=loser_id,
        harshness=_pair_harshness(world, scenario, card, loser_id, is_principal_pair),
        ceded_region_ids=ceded_regions(card, loser_id)
        if is_principal_pair and loser_id
        else [],
    )
    world.truces.append(truce)
    return truce


def _restore_peace_relations(
    world: WorldState, pairs: list[tuple[FactionId, FactionId]]
) -> None:
    for relation in world.relations:
        is_pair = (relation.faction_a, relation.faction_b) in pairs
        if is_pair and relation.status == RelationStatus.WAR:
            relation.status = RelationStatus.PEACE
            relation.since_turn = world.clock.turn


def _end_war(world: WorldState, war: WarState) -> None:
    world.wars = [item for item in world.wars if item.id != war.id]
    world.pressure.stalemate_turns.pop(war.id, None)


def sign_peace(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: UUID | str,
) -> list[EventLogEntry]:
    """Validate a confirmed peace card, apply its terms, end the war and bind a truce."""
    peace = _peace_term(card)
    war = find_war(world, peace.faction_a, peace.faction_b)
    if war is None or not pair_is_at_war(world, war, peace.faction_a, peace.faction_b):
        raise CampaignProgressError("no war to end", "no_war", 422)
    parties = signing_parties(peace)
    check_parties(war, peace, parties)
    _validate(world, scenario, card, war)
    events = breach_separate_peace(world, scenario, war, parties)
    pairs = open_pairs(world, war, parties)
    truces = [_create_truce(world, scenario, card, peace, war, pair) for pair in pairs]
    principal = tuple(sorted((peace.faction_a, peace.faction_b)))
    for term in card.terms:
        _apply_term(world, scenario, term, scene_id, truces[pairs.index(principal)])
    _restore_peace_relations(world, pairs)
    if all(pair in pairs for pair in remaining_pairs(world, war)):
        _end_war(world, war)
        events += settle_independence(world, war)
    return [*events, diplomacy_event(PEACE_SIGNED, parties)]
