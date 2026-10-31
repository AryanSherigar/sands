from uuid import uuid4

import pytest
from app.engine.negotiation import apply_terms_card
from app.engine.treaty.conditional_scan import scan_conditional_clauses
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import PhaseName
from strategy_contracts.condition_templates import ConditionClause, ConditionTemplate
from strategy_contracts.terms import (
    ConditionalMode,
    ConditionalTerm,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
)

from tests.engine.peace.builders import PLAYER, SCENARIO, WRATHFUL_RIVAL, make_world

THRESHOLD = 500
TURNS = 6
EXPIRY = 5


def _world():
    world = make_world()
    world.treaty_ruleset = 1
    world.factions[PLAYER].treasury = 0
    return world


def _tribute() -> TributeTerm:
    return TributeTerm(
        payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, gold_per_turn=1, duration_turns=TURNS
    )


def _trade() -> TradeDealTerm:
    return TradeDealTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=TURNS
    )


def _conditional(mode: ConditionalMode, inner) -> ConditionalTerm:
    return ConditionalTerm(
        mode=mode,
        when=ConditionClause(
            template=ConditionTemplate.TREASURY_ABOVE,
            faction_id=PLAYER,
            value=THRESHOLD,
        ),
        expires_in_turns=EXPIRY,
        inner=inner,
    )


def _sign(world, term):
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=WRATHFUL_RIVAL,
        terms=[term],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )
    return apply_terms_card(world, SCENARIO, card, uuid4())


def _scan(world):
    return scan_conditional_clauses(world, SCENARIO, PhaseName.ECONOMY)


def _of(world, term_type) -> list[CommitmentState]:
    return [item for item in world.commitments if isinstance(item.term, term_type)]


def test_trigger_signs_dormant_without_the_inner_clause() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.TRIGGER, _tribute()))

    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.DORMANT
    assert _of(world, TributeTerm) == []
    assert _scan(world) == []
    assert _of(world, TributeTerm) == []


def test_trigger_fires_once_when_the_condition_holds() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.TRIGGER, _tribute()))
    world.factions[PLAYER].treasury = THRESHOLD + 1

    events = _scan(world)

    assert [event.kind for event in events] == [
        "treaty_clause_signed",
        "conditional_clause_triggered",
    ]
    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.FULFILLED
    assert _of(world, TributeTerm)[0].status is CommitmentStatus.ACTIVE
    assert _scan(world) == []
    assert len(_of(world, TributeTerm)) == 1


def test_trigger_lapses_after_its_expiry() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.TRIGGER, _tribute()))
    world.clock.turn += EXPIRY + 1

    _scan(world)

    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.EXPIRED
    assert _of(world, TributeTerm) == []


def test_trigger_that_cannot_be_applied_fails_without_raising() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.TRIGGER, _tribute()))
    world.factions[PLAYER].treasury = 0
    term = _of(world, ConditionalTerm)[0].term.model_copy(
        update={
            "when": ConditionClause(
                template=ConditionTemplate.TURN_AFTER, faction_id=PLAYER, value=0
            )
        }
    )
    _of(world, ConditionalTerm)[0].term = term
    world.clock.turn = 1

    events = _scan(world)

    assert [event.kind for event in events] == ["conditional_clause_failed"]
    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.EXPIRED


def test_gate_starts_suspended_and_follows_the_condition() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.GATE, _trade()))
    trade = _of(world, TradeDealTerm)[0]
    assert trade.status is CommitmentStatus.SUSPENDED

    world.factions[PLAYER].treasury = THRESHOLD + 1
    opened = _scan(world)
    assert trade.status is CommitmentStatus.ACTIVE
    assert [event.kind for event in opened] == ["conditional_gate_opened"]
    assert _scan(world) == []

    world.factions[PLAYER].treasury = 0
    closed = _scan(world)
    assert trade.status is CommitmentStatus.SUSPENDED
    assert [event.kind for event in closed] == ["conditional_gate_closed"]


def test_gate_open_at_signing_starts_active() -> None:
    world = _world()
    world.factions[PLAYER].treasury = THRESHOLD + 1
    _sign(world, _conditional(ConditionalMode.GATE, _trade()))

    assert _of(world, TradeDealTerm)[0].status is CommitmentStatus.ACTIVE


def test_gate_expiry_ends_the_inner_clause() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.GATE, _trade()))
    world.clock.turn += EXPIRY + 1

    _scan(world)

    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.EXPIRED
    assert _of(world, TradeDealTerm)[0].status is CommitmentStatus.EXPIRED


def test_gate_with_an_unpayable_inner_clause_is_still_signable() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.GATE, _tribute()))

    assert _of(world, TributeTerm)[0].status is CommitmentStatus.SUSPENDED


def test_duplicate_conditional_clauses_are_refused() -> None:
    world = _world()
    term = _conditional(ConditionalMode.TRIGGER, _tribute())
    with pytest.raises(CampaignProgressError):
        card = TermsCard(
            proposer_id=PLAYER,
            counterpart_id=WRATHFUL_RIVAL,
            terms=[term, term],
            is_confirmed_by_player=True,
            is_confirmed_by_counterpart=True,
        )
        apply_terms_card(world, SCENARIO, card, uuid4())


def test_unlinked_commitments_keep_their_hash_shape() -> None:
    world = _world()
    _sign(world, _trade())
    dumped = world.commitments[0].model_dump(mode="json")
    assert "linked_commitment_id" not in dumped


def test_destroyed_party_lapses_a_trigger_quietly() -> None:
    world = _world()
    _sign(world, _conditional(ConditionalMode.TRIGGER, _tribute()))
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    assert _scan(world) == []
    assert _of(world, ConditionalTerm)[0].status is CommitmentStatus.EXPIRED
