from app.engine.diplomacy.phase import TimePhase
from app.engine.peace.breach import (
    breach_pressure,
    card_harshness,
    interaction_relief,
    recovery_gap,
    tick_breach,
)
from app.engine.peace.signing import sign_peace
from app.engine.rng import derive_rng
from app.models.world_diplomacy import CommitmentState, TruceState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm, TradeDealTerm

from tests.engine.diplomacy.builders import run_phase
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    region_owned_by,
    set_score,
)

TUNING = SCENARIO.tuning.peace


def _truce(harshness: int = 0, loser: str | None = WRATHFUL_RIVAL) -> TruceState:
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    return TruceState(
        id="truce_1",
        faction_a=first,
        faction_b=second,
        expires_turn=99,
        tier=PeaceTier.MEDIUM,
        loser_id=loser,
        harshness=harshness,
    )


def _rng(world):
    return derive_rng(world.rng.seed, world.clock.turn, "time")


def test_card_harshness_grows_with_ceded_regions() -> None:
    world = make_world()
    region = region_owned_by(world, WRATHFUL_RIVAL)
    cede = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region
    )
    mild = make_peace_card(PLAYER, WRATHFUL_RIVAL, [])
    harsh = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    assert card_harshness(world, SCENARIO, harsh, WRATHFUL_RIVAL) > card_harshness(
        world, SCENARIO, mild, WRATHFUL_RIVAL
    )


def test_capital_cession_adds_the_extinction_bonus() -> None:
    world = make_world()
    capital = world.factions[WRATHFUL_RIVAL].capital_region_id
    other = next(
        key
        for key, region in sorted(world.regions.items())
        if region.owner_id == WRATHFUL_RIVAL and key != capital
    )

    def _harshness(region_id: str) -> int:
        cede = CedeRegionTerm(
            from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region_id
        )
        card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])
        return card_harshness(world, SCENARIO, card, WRATHFUL_RIVAL)

    assert _harshness(capital) - _harshness(other) == TUNING.harshness_capital_bonus


def test_gold_share_counts_toward_harshness() -> None:
    world = make_world()
    treasury = world.factions[WRATHFUL_RIVAL].treasury
    gold = PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=treasury)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [gold])

    assert card_harshness(world, SCENARIO, card, WRATHFUL_RIVAL) > 0


def test_signing_records_loser_harshness_and_ceded_regions() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    region = region_owned_by(world, WRATHFUL_RIVAL)
    cede = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    sign_peace(world, SCENARIO, card, "scene-1")

    truce = world.truces[0]
    assert truce.loser_id == WRATHFUL_RIVAL
    assert truce.ceded_region_ids == [region]
    assert truce.harshness > 0


def test_recovery_gap_follows_war_exhaustion() -> None:
    world = make_world()
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 70

    assert recovery_gap(world, WRATHFUL_RIVAL) == 70


def test_trade_deal_and_alliance_lower_pressure() -> None:
    world = make_world()
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 80
    truce = _truce(harshness=80)
    world.truces.append(truce)
    before = breach_pressure(world, SCENARIO, truce)
    deal = TradeDealTerm(faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=9)
    world.commitments.append(
        CommitmentState(id="commitment_1", term=deal, start_turn=0, end_turn=9)
    )

    after = breach_pressure(world, SCENARIO, truce)

    assert interaction_relief(world, SCENARIO, truce) == TUNING.interaction_trade_relief
    assert after < before


def test_recovered_loser_has_lower_pressure() -> None:
    world = make_world()
    truce = _truce(harshness=80)
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 90
    tired = breach_pressure(world, SCENARIO, truce)
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 10

    assert breach_pressure(world, SCENARIO, truce) < tired


def test_pressure_is_bounded() -> None:
    world = make_world()
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 100
    truce = _truce(harshness=100)

    assert 0 <= breach_pressure(world, SCENARIO, truce) <= 100


def test_pressure_is_zero_without_truces() -> None:
    world = make_world()

    assert tick_breach(world, SCENARIO, _rng(world)) == []
    assert world.peace.breach == []


def _grieving_world():
    world = make_world()
    world.clock.turn = 10
    world.factions[WRATHFUL_RIVAL].war_exhaustion = 100
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace.grievance_pressure_threshold = 1
    world.truces.append(_truce(harshness=100))
    return world, scenario


def test_grievance_files_a_ground_once_per_cooldown() -> None:
    world, scenario = _grieving_world()
    scenario.tuning.peace.harshness_weight = 100

    tick_breach(world, scenario, _rng(world))
    first = len(world.grounds)
    world.clock.turn += 1
    tick_breach(world, scenario, _rng(world))

    assert first == 1
    assert len(world.grounds) == 1
    assert world.grounds[0].holder_faction_id == WRATHFUL_RIVAL
    assert world.grounds[0].kind in (GroundKind.CLAIM, GroundKind.INSULT)


def test_pressure_never_declares_war() -> None:
    world, scenario = _grieving_world()

    tick_breach(world, scenario, _rng(world))

    assert world.wars == []


def test_same_seed_gives_the_same_grievance() -> None:
    first, scenario = _grieving_world()
    second, _ = _grieving_world()

    tick_breach(first, scenario, _rng(first))
    tick_breach(second, scenario, _rng(second))

    assert first.grounds == second.grounds
    assert first.peace == second.peace


def test_time_phase_ticks_breach_pressure() -> None:
    world = make_world()
    world.clock.turn = 10
    world.truces.append(_truce(harshness=50))

    result = run_phase(TimePhase(), world)

    assert result.world.peace.breach[0].pressure >= 0
    assert CAUTIOUS_RIVAL not in result.world.peace.breach[0].faction_a


def test_an_expired_trade_deal_no_longer_relieves_pressure() -> None:
    world = make_world()
    truce = _truce(harshness=80)
    world.truces.append(truce)
    deal = TradeDealTerm(faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=9)
    world.commitments.append(
        CommitmentState(
            id="commitment_1", term=deal, start_turn=0, end_turn=world.clock.turn
        )
    )

    assert interaction_relief(world, SCENARIO, truce) == 0
