from app.engine.opinion import opinion_of, shift_opinion
from app.engine.succession.install import CAUSE_EVENT, kill_ruler
from app.models.world_character import MemoryState
from app.models.world_state import WorldState

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    leader_of,
    make_succession_world,
)
from tests.engine.succession.test_install import _with_heir

FADE = 2


def _regard(world: WorldState, holder: str, target: str) -> int:
    return opinion_of(leader_of(world, holder), world.factions[target].leader_id)


def _kill_wrathful_with_heir(world: WorldState):
    scenario = _with_heir(world, WRATHFUL_RIVAL)
    kill_ruler(world, scenario, WRATHFUL_RIVAL, CAUSE_EVENT)
    return scenario


def test_rivals_regard_for_the_dead_ruler_passes_to_the_successor() -> None:
    world = make_succession_world()
    shift_opinion(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "trade", 40, FADE)
    shift_opinion(world, PLAYER, WRATHFUL_RIVAL, "insult", -30, FADE)
    carry = SCENARIO.tuning.succession.opinion_carry_percent

    _kill_wrathful_with_heir(world)

    assert _regard(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == 40 * carry // 100
    assert _regard(world, PLAYER, WRATHFUL_RIVAL) == -(30 * carry // 100)


def test_inherited_reasons_keep_their_fade_and_name_their_origin() -> None:
    world = make_succession_world()
    shift_opinion(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "trade", 40, FADE)

    _kill_wrathful_with_heir(world)

    successor = world.factions[WRATHFUL_RIVAL].leader_id
    [reason] = leader_of(world, CAUTIOUS_RIVAL).opinions[successor].reasons
    assert (reason.cause, reason.fade_per_turn) == ("inherited:trade", FADE)


def _inherited_values(world: WorldState, holder: str, target: str) -> dict[str, int]:
    target_id = world.factions[target].leader_id
    opinion = leader_of(world, holder).opinions.get(target_id)
    reasons = [] if opinion is None else opinion.reasons
    return {item.cause: item.value for item in reasons if "inherited:" in item.cause}


def test_the_dead_rulers_own_opinions_pass_to_the_heir_scaled() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, "trade", 40, FADE)
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "insult", -30, FADE)
    carry = SCENARIO.tuning.succession.opinion_carry_percent

    _kill_wrathful_with_heir(world)

    trade = _inherited_values(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)
    insult = _inherited_values(world, WRATHFUL_RIVAL, PLAYER)
    assert trade["inherited:trade"] == 40 * carry // 100
    assert insult["inherited:insult"] == -(30 * carry // 100)


def test_the_heirs_inherited_regard_is_marked_with_its_origin() -> None:
    world = make_succession_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "insult", -30, FADE)

    _kill_wrathful_with_heir(world)

    player_id = world.factions[PLAYER].leader_id
    reasons = leader_of(world, WRATHFUL_RIVAL).opinions[player_id].reasons
    [reason] = [item for item in reasons if item.cause == "inherited:insult"]
    assert reason.fade_per_turn == FADE


def test_the_dead_rulers_memories_pass_to_the_heir_scaled_and_marked() -> None:
    world = make_succession_world()
    player_id = world.factions[PLAYER].leader_id
    leader_of(world, WRATHFUL_RIVAL).memories.append(
        MemoryState(kind="talks_broken_off", turn=2, subject_id=player_id, weight=-12)
    )
    carry = SCENARIO.tuning.succession.opinion_carry_percent

    _kill_wrathful_with_heir(world)

    [memory] = leader_of(world, WRATHFUL_RIVAL).memories
    assert memory.kind == "inherited:talks_broken_off"
    assert (memory.turn, memory.subject_id) == (2, player_id)
    assert memory.weight == -(12 * carry // 100)


def test_a_legacy_world_does_not_carry_opinions() -> None:
    world = make_succession_world()
    world.succession_ruleset = 1
    shift_opinion(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "trade", 40, FADE)

    _kill_wrathful_with_heir(world)

    assert _regard(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == 0


def test_a_zero_carry_percent_inherits_nothing() -> None:
    world = make_succession_world()
    shift_opinion(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "trade", 40, FADE)
    scenario = _with_heir(world, WRATHFUL_RIVAL)
    scenario.tuning.succession.opinion_carry_percent = 0

    kill_ruler(world, scenario, WRATHFUL_RIVAL, CAUSE_EVENT)

    assert _regard(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == 0


def test_a_legacy_world_does_not_carry_the_dead_rulers_regard() -> None:
    world = make_succession_world()
    world.succession_ruleset = 1
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, "insult", -30, FADE)

    _kill_wrathful_with_heir(world)

    assert _regard(world, WRATHFUL_RIVAL, PLAYER) == 0
