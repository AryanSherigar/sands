from app.engine.diplomacy.grounds import grant_ground
from app.engine.opinion import shift_opinion
from app.engine.succession.install import CAUSE_EVENT, kill_ruler
from app.services.scene_grudges import MAX_GRUDGES_PER_SCENE, build_grudges
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.scene import GrudgeBand, GrudgeSource
from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    leader_of,
    make_succession_world,
)
from tests.engine.succession.test_install import _with_heir

FADE = 1


def _grudges(world, scenario=SCENARIO, faction=WRATHFUL_RIVAL):
    return build_grudges(world, scenario, leader_of(world, faction), PLAYER)


def test_a_negative_opinion_reason_becomes_a_readable_grudge() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "refused_call", -30, FADE)

    [grudge] = [
        item
        for item in _grudges(world)
        if item.text == "You refused their call to arms."
    ]

    assert grudge.source is GrudgeSource.OPINION
    assert grudge.band is GrudgeBand.FIRM
    assert not grudge.is_inherited


def test_goodwill_and_other_leaders_are_not_grudges() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "trade", 40, FADE)
    shift_opinion(world, CAUTIOUS_RIVAL, PLAYER, "insult", -40, FADE)

    texts = [item.text for item in _grudges(world)]

    assert "Trade." not in texts
    assert "Insult." not in texts


def test_authored_grudge_text_passes_through() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "You burned our granaries.", -60, FADE)

    [grudge] = [item for item in _grudges(world) if "granaries" in item.text]

    assert grudge.text == "You burned our granaries."
    assert grudge.band is GrudgeBand.BURNING


def test_an_active_ground_against_the_player_is_a_grudge() -> None:
    world = make_succession_world()
    grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.INSULT,
        holder_faction_id=WRATHFUL_RIVAL,
        target_faction_id=PLAYER,
    )

    texts = [(item.text, item.source) for item in _grudges(world)]

    assert ("You insulted them.", GrudgeSource.GROUND) in texts


def test_a_ground_against_someone_else_is_not_listed() -> None:
    world = make_succession_world()
    grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.INSULT,
        holder_faction_id=WRATHFUL_RIVAL,
        target_faction_id=CAUTIOUS_RIVAL,
    )

    assert all(item.source is not GrudgeSource.GROUND for item in _grudges(world))


def test_an_heir_speaks_for_the_dead_rulers_grudges() -> None:
    world = make_succession_world()
    predecessor = leader_of(world, WRATHFUL_RIVAL)
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "refused_call", -60, FADE)
    grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.BROKEN_PROMISE,
        holder_faction_id=WRATHFUL_RIVAL,
        target_faction_id=PLAYER,
    )
    scenario = _with_heir(world, WRATHFUL_RIVAL)

    kill_ruler(world, scenario, WRATHFUL_RIVAL, CAUSE_EVENT)

    grudges = _grudges(world, scenario)
    assert grudges
    assert all(item.is_inherited for item in grudges)
    assert {item.predecessor_name for item in grudges} == {predecessor.name}


def test_ids_follow_strength_order_and_are_capped() -> None:
    world = make_succession_world()
    for position in range(MAX_GRUDGES_PER_SCENE + 3):
        shift_opinion(
            world, WRATHFUL_RIVAL, PLAYER, f"Wrong {position}.", -10 - position, FADE
        )

    grudges = _grudges(world)

    assert [item.id for item in grudges] == [
        f"g{i}" for i in range(1, MAX_GRUDGES_PER_SCENE + 1)
    ]
    texts = [item.text for item in grudges]
    assert f"Wrong {MAX_GRUDGES_PER_SCENE + 2}." in texts
    assert "Wrong 0." not in texts


def test_two_builds_of_the_same_world_agree() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "refused_demand", -25, FADE)
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "refused_call", -25, FADE)

    assert _grudges(world) == _grudges(world)
