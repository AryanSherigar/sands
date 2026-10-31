from app.engine.diplomacy.grounds import (
    act_threshold,
    current_strength,
    expire_grounds,
    fade_per_turn,
    forgive,
    grant_ground,
    grant_insult_ground,
    inherit_grounds,
    is_usable,
)
from app.models.world_diplomacy import GroundState
from strategy_contracts.diplomacy import GroundKind

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

HOLDER = WRATHFUL_RIVAL
TARGET = PLAYER
REGION = "brennmoor"


def _claim(world, holder: str = HOLDER) -> GroundState:
    return grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=holder,
        target_faction_id=TARGET,
        region_id=REGION,
    )


def _leader(world, faction_id: str):
    return world.leaders[world.factions[faction_id].leader_id]


def test_fade_follows_ruler_temperament() -> None:
    world = make_world()
    expected = {
        "neutral": ([], 2),
        "wrathful": (["wrathful"], 1),
        "trusting": (["trusting"], 3),
        "cautious": (["cautious"], 4),
    }
    for traits, fade in expected.values():
        leader_id = set_traits(world, HOLDER, traits)
        assert fade_per_turn(world.leaders[leader_id], SCENARIO) == fade


def test_aggressive_threshold_below_neutral_below_cautious() -> None:
    world = make_world()
    ground = _claim(world)
    thresholds = {}
    for name, traits in (
        ("wrathful", ["wrathful"]),
        ("neutral", []),
        ("cautious", ["cautious"]),
    ):
        leader_id = set_traits(world, HOLDER, traits)
        thresholds[name] = act_threshold(
            ground, world.leaders[leader_id], SCENARIO, world
        )

    assert thresholds == {"wrathful": 20, "neutral": 50, "cautious": 75}


def test_honor_raises_threshold_for_insults_not_claims() -> None:
    world = make_world()
    leader_id = set_traits(world, HOLDER, ["honorable"])
    claim = _claim(world)
    insult = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.INSULT,
        holder_faction_id=HOLDER,
        target_faction_id=TARGET,
    )
    leader = world.leaders[leader_id]

    assert act_threshold(claim, leader, SCENARIO, world) == 55
    assert act_threshold(insult, leader, SCENARIO, world) == 70


def test_greed_lowers_threshold_on_wealthy_claim_region() -> None:
    world = make_world()
    leader_id = set_traits(world, HOLDER, ["pragmatic"])
    claim = _claim(world)
    leader = world.leaders[leader_id]
    poor = act_threshold(claim, leader, SCENARIO, world)
    world.regions[REGION].wealth = SCENARIO.tuning.diplomacy.wealthy_region_wealth

    assert act_threshold(claim, leader, SCENARIO, world) == poor - 5


def test_strength_fades_by_fade_per_turn() -> None:
    world = make_world()
    leader_id = set_traits(world, HOLDER, [])
    ground = _claim(world)

    assert current_strength(ground, world.leaders[leader_id], SCENARIO, 10) == 80


def test_immature_forgery_has_no_strength() -> None:
    world = make_world()
    leader_id = set_traits(world, HOLDER, [])
    ground = _claim(world)
    ground.matures_turn = 3

    assert current_strength(ground, world.leaders[leader_id], SCENARIO, 2) == 0


def test_unusable_when_leader_changed() -> None:
    world = make_world()
    set_traits(world, HOLDER, ["wrathful"])
    ground = _claim(world)
    assert is_usable(world, SCENARIO, ground)

    ground.holder_leader_id = "someone_else"

    assert not is_usable(world, SCENARIO, ground)


def test_weak_ground_is_not_usable_for_a_cautious_ruler() -> None:
    world = make_world()
    set_traits(world, HOLDER, ["cautious"])
    ground = _claim(world)
    ground.strength = 74

    assert not is_usable(world, SCENARIO, ground)


def test_renewal_resets_instead_of_duplicating() -> None:
    world = make_world()
    first = _claim(world)
    first.strength = 10
    world.clock.turn = 4

    second = _claim(world)

    assert len(world.grounds) == 1
    assert second.id == first.id
    assert (second.strength, second.since_turn) == (100, 4)


def test_insult_grade_zero_grants_nothing() -> None:
    world = make_world()

    result = grant_insult_ground(
        world, SCENARIO, holder_faction_id=HOLDER, target_faction_id=TARGET, grade=0
    )

    assert result is None
    assert world.grounds == []


def test_insult_grade_scales_strength_and_is_capped_per_turn() -> None:
    world = make_world()

    first = grant_insult_ground(
        world, SCENARIO, holder_faction_id=HOLDER, target_faction_id=TARGET, grade=2
    )
    second = grant_insult_ground(
        world,
        SCENARIO,
        holder_faction_id=HOLDER,
        target_faction_id=CAUTIOUS_RIVAL,
        grade=4,
    )

    assert first is not None and first.strength == 40
    assert second is None


def test_heir_keeps_half_of_claim_and_quarter_of_insult() -> None:
    world = make_world()
    claim = _claim(world)
    insult = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.INSULT,
        holder_faction_id=HOLDER,
        target_faction_id=TARGET,
    )

    inherit_grounds(world, SCENARIO, HOLDER, "new_leader")

    assert (claim.strength, claim.holder_leader_id) == (50, "new_leader")
    assert (insult.strength, insult.holder_leader_id) == (5, "new_leader")


def test_expire_removes_only_faded_matured_grounds() -> None:
    world = make_world()
    set_traits(world, HOLDER, [])
    faded = _claim(world)
    faded.strength = 2
    immature = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=HOLDER,
        target_faction_id=CAUTIOUS_RIVAL,
        region_id="elmstead",
    )
    immature.matures_turn = 5
    world.clock.turn = 1

    removed = expire_grounds(world, SCENARIO)

    assert [ground.id for ground in removed] == [faded.id]
    assert world.grounds == [immature]


def test_forgive_lowers_strength_without_going_negative() -> None:
    world = make_world()
    ground = _claim(world)

    forgive(world, SCENARIO, HOLDER, TARGET, amount=30)
    assert ground.strength == 70
    forgive(world, SCENARIO, HOLDER, TARGET, amount=500)
    assert ground.strength == 0
