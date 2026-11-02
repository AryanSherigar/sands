import random

from app.engine.diplomacy.npc_captives import act_on_player_captives
from app.engine.diplomacy.phase import TimePhase
from app.engine.diplomacy.prisoner_curve import prisoner_curve
from app.engine.diplomacy.prisoners import handle_prisoner, ransom_price
from app.engine.diplomacy.ransom_verdict import (
    RansomResponse,
    ransom_verdict,
    ransom_willingness,
)
from app.engine.overtures.arming import arm_overture
from app.engine.pressure.captivity import captive_drain
from app.engine.pressure.mercy import mercy_total
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import run_phase, set_traits
from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TRAIT_POOL = (
    "honorable",
    "treacherous",
    "proud",
    "wrathful",
    "cautious",
    "pragmatic",
    "cunning",
    "cruel",
    "trusting",
)
ORDER_ACTIONS = ("release", "execute", "ransom")
TUNING = SCENARIO.tuning.peace
SEEDS = range(40)
TURNS = 14


def _random_world(rng: random.Random):
    world = make_world()
    if rng.random() < 0.6:
        add_war(world)
    world.factions[WRATHFUL_RIVAL].stability = rng.randint(0, 100)
    world.factions[WRATHFUL_RIVAL].treasury = rng.choice((0, 30, 500, 100000))
    world.factions[PLAYER].treasury = rng.choice((0, 200, 100000))
    set_traits(world, WRATHFUL_RIVAL, rng.sample(TRAIT_POOL, 2))
    set_traits(world, PLAYER, rng.sample(TRAIT_POOL, 2))
    for index in range(rng.randint(1, 5)):
        holder, origin = rng.choice(
            ((PLAYER, WRATHFUL_RIVAL), (WRATHFUL_RIVAL, PLAYER))
        )
        count = rng.choice((1, 5, 40, 300, 2500))
        world.prisoners.append(
            PrisonerState(
                id=f"prisoner_{index}",
                held_by_id=holder,
                origin_faction_id=origin,
                kind=PrisonerKind.TROOPS,
                troop_count=count,
                origin_battle_id="battle_1",
                troops_by_type={TroopType.INFANTRY: count},
            )
        )
    return world


def _check_invariants(world) -> None:
    ids = [item.id for item in world.prisoners]
    assert len(ids) == len(set(ids))
    for faction in world.factions.values():
        assert faction.treasury >= 0
        assert 0 <= faction.stability <= 100
        assert -100 <= faction.reputation <= 100
    for army in world.armies.values():
        assert 0 <= army.morale <= 100
    for counter in world.peace.ransom_counters:
        assert counter.gold >= 0


def _random_order(world, rng: random.Random) -> HandlePrisonerOrder | None:
    mine = [item for item in world.prisoners if item.held_by_id == PLAYER]
    if not mine:
        return None
    prisoner = rng.choice(mine)
    return HandlePrisonerOrder(
        faction_id=PLAYER,
        prisoner_id=prisoner.id,
        action=rng.choice(ORDER_ACTIONS),
    )


def _play(seed: int):
    rng = random.Random(seed)
    world = _random_world(rng)
    for _ in range(TURNS):
        world.clock.turn += 1
        order = _random_order(world, rng)
        if order is not None:
            handle_prisoner(world, SCENARIO, order)
        world = run_phase(TimePhase(), world).world
        arm_overture(world, SCENARIO)
        world.progress.pending_scene_id = None
        world.progress.pending_negotiation = None
        _check_invariants(world)
    return world


def test_random_games_never_break_the_core_invariants() -> None:
    for seed in SEEDS:
        _play(seed)


def test_random_games_replay_to_the_same_world() -> None:
    from app.engine.hashing import world_hash

    for seed in SEEDS:
        assert world_hash(_play(seed)) == world_hash(_play(seed))


def test_counters_only_ever_point_at_prisoners_the_player_still_holds() -> None:
    for seed in SEEDS:
        world = _play(seed)
        held = {item.id for item in world.prisoners if item.held_by_id == PLAYER}
        for counter in world.peace.ransom_counters:
            assert counter.prisoner_id in held


def test_the_prisoner_curve_is_monotone_and_bounded_everywhere() -> None:
    previous = 0
    for troops in range(0, 200_000, 137):
        points = prisoner_curve(troops, 20, 1000)
        assert previous <= points <= 20
        previous = points


def test_a_more_desperate_realm_is_never_less_willing_to_pay() -> None:
    for seed in SEEDS:
        world = _random_world(random.Random(seed))
        prisoner = next((p for p in world.prisoners if p.held_by_id == PLAYER), None)
        if prisoner is None:
            continue
        origin = world.factions[prisoner.origin_faction_id]
        willingness = []
        for stability in (100, 70, 40, 10, 0):
            origin.stability = stability
            willingness.append(ransom_willingness(world, SCENARIO, prisoner))
        assert willingness == sorted(willingness)


def test_the_verdict_is_ordered_by_willingness_and_never_overspends() -> None:
    rank = {
        RansomResponse.REFUSE: 0,
        RansomResponse.HAGGLE: 1,
        RansomResponse.ACCEPT: 2,
    }
    for seed in SEEDS:
        world = _random_world(random.Random(seed))
        for prisoner in world.prisoners:
            price = ransom_price(prisoner, TUNING)
            verdict = ransom_verdict(world, SCENARIO, prisoner, price)
            treasury = world.factions[prisoner.origin_faction_id].treasury
            if verdict.response is RansomResponse.ACCEPT:
                assert treasury >= price
            if verdict.response is RansomResponse.HAGGLE:
                assert 0 < verdict.counter_gold <= min(price, treasury)
            if verdict.response is RansomResponse.REFUSE:
                assert verdict.counter_gold == 0
            assert rank[verdict.response] in (0, 1, 2)


def test_pressure_readings_stay_inside_their_caps() -> None:
    for seed in SEEDS:
        world = _play(seed)
        for faction_id in (PLAYER, WRATHFUL_RIVAL):
            assert (
                0
                <= captive_drain(world, SCENARIO, faction_id)
                <= (TUNING.captive_drain_cap)
            )
            assert abs(mercy_total(world, SCENARIO, faction_id)) <= (
                TUNING.mercy_will_cap
            )


def test_npc_decisions_never_leave_a_dangling_prisoner() -> None:
    for seed in SEEDS:
        world = _random_world(random.Random(seed))
        for _ in range(8):
            world.clock.turn += 1
            act_on_player_captives(world, SCENARIO)
            _check_invariants(world)
