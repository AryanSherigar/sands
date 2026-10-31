from app.engine.ai.aims import aim_is_valid, choose_aim, pick_target, refresh_aim
from app.engine.rng import DeterministicRng
from app.models.world_character import OpinionReason, OpinionState
from app.models.world_diplomacy import GroundState, WarState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

SEEDS = range(40)


def _world(stance: str | None = None):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, [])
    world.factions[CAUTIOUS_RIVAL].stance.option_id = stance
    return world


def _add_war(world, attacker: str, defender: str) -> None:
    world.wars.append(
        WarState(id="war_1", attacker_id=attacker, defender_id=defender, started_turn=0)
    )


def _add_ground(world, holder: str, target: str, strength: int = 50) -> None:
    holder_leader = world.factions[holder].leader_id
    region_id = sorted(world.regions)[0]
    world.grounds.append(
        GroundState(
            id="ground_1",
            kind=GroundKind.CLAIM,
            holder_faction_id=holder,
            holder_leader_id=holder_leader,
            target_faction_id=target,
            region_id=region_id,
            strength=strength,
            since_turn=0,
            is_personal=False,
        )
    )


def _choose(world, faction: str = CAUTIOUS_RIVAL, seed: int = 1):
    return choose_aim(world, SCENARIO, faction, DeterministicRng(seed))


def test_rebuild_stance_drives_a_build_aim() -> None:
    world = _world("rebuild")

    for seed in SEEDS:
        assert _choose(world, seed=seed).aim.category == ScoreCategory.BUILD


def test_attack_aim_needs_a_target() -> None:
    world = _world("revenge_on_player")

    for seed in SEEDS:
        assert _choose(world, seed=seed).aim.category != ScoreCategory.ATTACK


def test_war_enemy_becomes_the_attack_target() -> None:
    world = _world("revenge_on_player")
    _add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    for seed in SEEDS:
        aim = _choose(world, seed=seed).aim
        assert (aim.category, aim.target_faction_id) == (
            ScoreCategory.ATTACK,
            WRATHFUL_RIVAL,
        )


def test_target_prefers_war_then_ground_then_worst_opinion() -> None:
    world = _world()
    assert pick_target(world, CAUTIOUS_RIVAL) is None
    assert pick_target(world, WRATHFUL_RIVAL) == PLAYER
    _add_ground(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)
    assert pick_target(world, WRATHFUL_RIVAL) == CAUTIOUS_RIVAL
    _add_war(world, WRATHFUL_RIVAL, PLAYER)
    assert pick_target(world, WRATHFUL_RIVAL) == PLAYER


def test_leaderless_faction_gets_no_aim() -> None:
    world = _world("rebuild")
    world.factions[CAUTIOUS_RIVAL].leader_id = None

    assert _choose(world) is None
    assert refresh_aim(world, SCENARIO, CAUTIOUS_RIVAL, DeterministicRng(1)) is None
    assert CAUTIOUS_RIVAL not in world.aims


def test_refresh_sets_an_aim_once_and_keeps_it() -> None:
    world = _world("rebuild")

    first = refresh_aim(world, SCENARIO, CAUTIOUS_RIVAL, DeterministicRng(1))
    aim = world.aims[CAUTIOUS_RIVAL]
    second = refresh_aim(world, SCENARIO, CAUTIOUS_RIVAL, DeterministicRng(2))

    assert first is not None
    assert (first.kind, first.cause.summary_key) == ("ai_aim_set", "ai_aim_build")
    assert second is None
    assert world.aims[CAUTIOUS_RIVAL] == aim


def _aim(world):
    refresh_aim(world, SCENARIO, CAUTIOUS_RIVAL, DeterministicRng(1))
    return world.aims[CAUTIOUS_RIVAL]


def test_aim_is_valid_until_the_stance_changes() -> None:
    world = _world("rebuild")
    aim = _aim(world)
    assert aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)

    world.factions[CAUTIOUS_RIVAL].stance.option_id = "turtle"

    assert not aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)


def test_aim_ends_when_the_leader_changes() -> None:
    world = _world("rebuild")
    aim = _aim(world)
    world.factions[CAUTIOUS_RIVAL].leader_id = "heir"

    assert not aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)


def test_aim_ends_after_the_maximum_age() -> None:
    world = _world("rebuild")
    aim = _aim(world)
    world.clock.turn += SCENARIO.tuning.ai.aim_max_turns

    assert not aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)


def test_aim_ends_when_the_capital_changes_hands() -> None:
    world = _world("rebuild")
    aim = _aim(world)
    capital = world.factions[CAUTIOUS_RIVAL].capital_region_id
    world.regions[capital].owner_id = WRATHFUL_RIVAL

    assert not aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)


def test_aim_ends_when_the_target_is_destroyed() -> None:
    world = _world("revenge_on_player")
    _add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
    aim = _aim(world)
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    assert not aim_is_valid(world, SCENARIO, CAUTIOUS_RIVAL, aim)


def _hoard_picks(treasury: int) -> int:
    world = _world()
    world.factions[CAUTIOUS_RIVAL].treasury = treasury
    picks = [_choose(world, seed=seed).aim.category for seed in SEEDS]
    return picks.count(ScoreCategory.HOARD)


def test_low_treasury_pushes_toward_hoarding() -> None:
    assert _hoard_picks(treasury=1) > _hoard_picks(treasury=1000)


def _warm_opinion(world, value: int) -> None:
    leader_id = world.factions[CAUTIOUS_RIVAL].leader_id
    target_leader = world.factions[WRATHFUL_RIVAL].leader_id
    world.leaders[leader_id].opinions[target_leader] = OpinionState(
        target_id=target_leader,
        reasons=[OpinionReason(cause="shared feast", value=value, fade_per_turn=0)],
    )


def test_ally_aim_courts_the_warmest_neighbour() -> None:
    world = _world("court_ally")
    _warm_opinion(world, 30)

    for seed in SEEDS:
        aim = _choose(world, seed=seed).aim
        assert (aim.category, aim.target_faction_id) == (
            ScoreCategory.ALLY,
            WRATHFUL_RIVAL,
        )


def test_ally_aim_without_warm_feelings_has_no_target() -> None:
    world = _world("court_ally")
    _warm_opinion(world, -30)

    assert _choose(world).aim.target_faction_id is None


def test_ally_target_is_never_the_player_or_an_enemy() -> None:
    world = _world("court_ally")
    _warm_opinion(world, 30)
    _add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert _choose(world).aim.target_faction_id is None
