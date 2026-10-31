from app.engine.opinion import opinion_of, shift_opinion

from tests.engine.alliances.builders import CAUTIOUS_RIVAL, PLAYER, make_world

FADE = 1


def _leader(world, faction_id: str):
    return world.leaders[world.factions[faction_id].leader_id]


def test_shift_opinion_lowers_the_holders_view_of_the_target_leader() -> None:
    world = make_world()
    holder = _leader(world, PLAYER)
    target = _leader(world, CAUTIOUS_RIVAL)
    before = opinion_of(holder, target.id)

    shift_opinion(world, PLAYER, CAUTIOUS_RIVAL, "refused_call", -10, FADE)

    assert opinion_of(holder, target.id) == before - 10


def test_shift_opinion_accumulates_reasons() -> None:
    world = make_world()
    shift_opinion(world, PLAYER, CAUTIOUS_RIVAL, "refused_call", -10, FADE)
    shift_opinion(world, PLAYER, CAUTIOUS_RIVAL, "refused_call", -5, FADE)

    opinion = _leader(world, PLAYER).opinions[_leader(world, CAUTIOUS_RIVAL).id]
    assert [reason.value for reason in opinion.reasons][-2:] == [-10, -5]


def test_shift_opinion_ignores_leaderless_factions() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].leader_id = None

    shift_opinion(world, PLAYER, CAUTIOUS_RIVAL, "refused_call", -10, FADE)

    assert world.factions[CAUTIOUS_RIVAL].leader_id is None
