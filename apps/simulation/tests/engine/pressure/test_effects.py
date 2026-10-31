from app.engine.internal.phase import InternalPhase
from app.engine.negotiation import acceptance_range
from app.engine.phases import PhaseContext
from app.engine.pressure.effects import (
    acceptance_shift,
    pressure_stability_loss,
    pressure_unrest,
)
from app.engine.rng import derive_rng

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)


def _exhaust(world, faction_id: str) -> None:
    set_traits(world, faction_id, ["pragmatic"])
    for region in world.regions.values():
        if region.owner_id == faction_id:
            region.manpower, region.unrest = 0, 100
            world.pressure.devastation[region.id] = 100
    world.factions[faction_id].treasury = 0
    world.factions[faction_id].stability = 10
    for army in world.armies.values():
        if army.owner_id == faction_id:
            army.morale = 0


def _comfort(world, faction_id: str) -> None:
    set_traits(world, faction_id, ["pragmatic"])
    world.factions[faction_id].stability = 80
    for army in world.armies.values():
        if army.owner_id == faction_id:
            army.morale = 100


def _context() -> PhaseContext:
    return PhaseContext(
        scenario=SCENARIO,
        orders=(),
        rng=derive_rng(7, 1, "internal"),
        resolved_outcomes={},
        recorded_answers={},
    )


def test_comfortable_faction_has_no_extra_loss() -> None:
    world = make_world()
    add_war(world)
    _comfort(world, PLAYER)

    assert pressure_stability_loss(world, SCENARIO, PLAYER) == 0
    assert pressure_unrest(world, SCENARIO, PLAYER) == 0


def test_high_strain_and_low_will_cost_stability_and_unrest() -> None:
    world = make_world()
    add_war(world)
    _exhaust(world, PLAYER)

    assert pressure_stability_loss(world, SCENARIO, PLAYER) > 0
    assert pressure_unrest(world, SCENARIO, PLAYER) > 0


def test_peace_faction_has_no_effects() -> None:
    world = make_world()
    _exhaust(world, PLAYER)

    assert pressure_stability_loss(world, SCENARIO, PLAYER) == 0
    assert acceptance_shift(world, SCENARIO, PLAYER) == 0


def test_extreme_pressure_drains_stability_faster_than_baseline() -> None:
    pressured, baseline = make_world(), make_world()
    for world in (pressured, baseline):
        add_war(world)
        _exhaust(world, PLAYER)
        world.factions[PLAYER].stability = 60
    baseline.pressure_ruleset = 0

    InternalPhase().run(pressured, _context())
    InternalPhase().run(baseline, _context())

    assert pressured.factions[PLAYER].stability < baseline.factions[PLAYER].stability


def test_pressure_never_ends_the_war_for_the_player() -> None:
    world = make_world()
    add_war(world)
    _exhaust(world, PLAYER)

    InternalPhase().run(world, _context())

    assert [war.id for war in world.wars] == ["war_1"]
    assert world.plays == []


def _counterpart_world(is_exhausted: bool):
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)
    set_traits(world, WRATHFUL_RIVAL, ["wrathful"])
    if is_exhausted:
        _exhaust(world, WRATHFUL_RIVAL)
    else:
        _comfort(world, WRATHFUL_RIVAL)
    return world


def test_acceptance_range_eases_for_exhausted_leader() -> None:
    fresh = acceptance_range(
        _counterpart_world(False), SCENARIO, PLAYER, WRATHFUL_RIVAL
    )
    spent = acceptance_range(_counterpart_world(True), SCENARIO, PLAYER, WRATHFUL_RIVAL)

    assert spent.accept_at < fresh.accept_at
    assert spent.accept_at - spent.haggle_at == fresh.accept_at - fresh.haggle_at


def test_acceptance_range_unchanged_when_ruleset_zero() -> None:
    exhausted, comfortable = _counterpart_world(True), _counterpart_world(False)
    exhausted.pressure_ruleset = comfortable.pressure_ruleset = 0

    assert acceptance_range(exhausted, SCENARIO, PLAYER, WRATHFUL_RIVAL) == (
        acceptance_range(comfortable, SCENARIO, PLAYER, WRATHFUL_RIVAL)
    )
