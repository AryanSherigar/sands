from app.engine.commands.phases import CampaignEconomyPhase
from app.engine.peace.truces import breach_agreements
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.engine.treaty.effects import is_in_force
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from strategy_contracts.terms import Term, TradeDealTerm, TributeTerm

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    events_of,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    run_economy,
)
from tests.engine.peace.builders import set_war_relation

START_TREASURY = 100
INCOME = 100
TRADE_PERCENT = 10
TERM_TURNS = 6


def _world(term: Term, end_turn: int | None = None, ruleset: int = 1) -> WorldState:
    world = make_world(
        regions=[
            make_region("home", PLAYER, wealth=INCOME),
            make_region("fief", RIVAL, wealth=INCOME),
        ],
        factions=[
            make_faction(PLAYER, treasury=START_TREASURY),
            make_faction(RIVAL, treasury=START_TREASURY),
        ],
    )
    world.treaty_ruleset = ruleset
    ends = world.clock.turn + TERM_TURNS if end_turn is None else end_turn
    world.commitments.append(
        CommitmentState(
            id="commitment_1", term=term, start_turn=world.clock.turn, end_turn=ends
        )
    )
    return world


def _trade() -> TradeDealTerm:
    return TradeDealTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=TERM_TURNS)


def _tribute(gold: int) -> TributeTerm:
    return TributeTerm(
        payer_id=RIVAL, payee_id=PLAYER, gold_per_turn=gold, duration_turns=TERM_TURNS
    )


def test_trade_deal_credits_both_parties_a_share_of_their_income() -> None:
    result = run_economy(_world(_trade()))

    gain = INCOME * TRADE_PERCENT // 100
    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME + gain
    assert result.world.factions[RIVAL].treasury == START_TREASURY + INCOME + gain
    assert len(events_of(result, "trade_income")) == 1


def test_expired_trade_deal_pays_nothing() -> None:
    world = _world(_trade())
    world.commitments[0].end_turn = world.clock.turn

    result = run_economy(world)

    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME
    assert events_of(result, "trade_income") == []


def test_trade_deal_pays_nothing_below_the_treaty_ruleset() -> None:
    result = run_economy(_world(_trade(), ruleset=0))

    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME


def test_declaring_war_voids_the_trade_deal() -> None:
    world = _world(_trade())

    breach_agreements(world, make_scenario(), PLAYER, RIVAL)

    assert world.commitments[0].status is CommitmentStatus.EXPIRED
    assert run_economy(world).world.factions[PLAYER].treasury == (
        START_TREASURY + INCOME
    )


def test_a_trade_deal_between_warring_realms_is_not_in_force() -> None:
    world = _world(_trade())
    assert is_in_force(world, world.commitments[0]) is True

    set_war_relation(world, PLAYER, RIVAL)

    assert is_in_force(world, world.commitments[0]) is False


def test_tribute_moves_gold_from_payer_to_payee() -> None:
    result = run_economy(_world(_tribute(30)))

    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME + 30
    assert result.world.factions[RIVAL].treasury == START_TREASURY + INCOME - 30
    assert len(events_of(result, "tribute_paid")) == 1


def test_tribute_never_exceeds_the_payers_cash() -> None:
    world = _world(_tribute(5000))

    result = run_economy(world)

    assert result.world.factions[RIVAL].treasury >= 0
    paid = START_TREASURY + INCOME - result.world.factions[RIVAL].treasury
    assert 0 < paid < 5000


def test_the_campaign_economy_phase_pays_trade_and_tribute_too() -> None:
    world = _world(_trade())
    world.commitments.append(
        CommitmentState(
            id="commitment_2",
            term=_tribute(10),
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + TERM_TURNS,
        )
    )
    scenario = make_scenario()
    context = PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(world.rng.seed, world.clock.turn, PhaseName.ECONOMY.value),
        resolved_outcomes={},
        recorded_answers={},
    )

    result = CampaignEconomyPhase().run(world, context)

    kinds = [event.kind for event in result.events]
    assert "trade_income" in kinds
    assert "tribute_paid" in kinds
