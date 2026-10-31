from app.engine.diplomacy.phase import TimePhase
from app.engine.phases import PhaseContext
from app.engine.pressure.phase import tick_pressure
from app.engine.rng import derive_rng
from app.models.world_region import OccupationState
from strategy_contracts.pressure import ShockKind

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)


def _rng():
    return derive_rng(7, 1, "pressure")


def _tick(world):
    return tick_pressure(world, SCENARIO, _rng())


def test_tick_files_capital_fall_shock_once() -> None:
    world = make_world()
    add_war(world)
    capital = world.regions[world.factions[PLAYER].capital_region_id]
    capital.occupation = OccupationState(occupier_id=WRATHFUL_RIVAL, siege_progress=100)

    _tick(world)
    _tick(world)

    kinds = [s.kind for s in world.pressure.shocks if s.kind is ShockKind.CAPITAL_FALLS]
    assert len(kinds) == 1


def test_tick_raises_devastation_where_enemy_armies_stand() -> None:
    world = make_world()
    add_war(world)
    home = next(r for r in world.regions.values() if r.owner_id == PLAYER)
    raider = next(a for a in world.armies.values() if a.owner_id == WRATHFUL_RIVAL)
    raider.location_id = home.id

    _tick(world)

    assert world.pressure.devastation[home.id] > 0


def test_tick_raises_devastation_in_occupied_regions() -> None:
    world = make_world()
    add_war(world)
    home = next(r for r in world.regions.values() if r.owner_id == PLAYER)
    home.occupation = OccupationState(occupier_id=WRATHFUL_RIVAL, siege_progress=100)

    _tick(world)

    assert world.pressure.devastation[home.id] > 0


def test_tick_emits_event_only_on_band_change() -> None:
    world = make_world()
    add_war(world)
    set_traits(world, PLAYER, ["pragmatic"])

    _tick(world)
    quiet = _tick(world)
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.morale = 0
    world.factions[PLAYER].stability = 0
    changed = _tick(world)

    assert [e for e in quiet if e.kind == "pressure_band_changed"] == []
    assert [
        e.cause.subject_ids[0] for e in changed if e.kind == "pressure_band_changed"
    ] == [PLAYER]


def test_tick_skips_factions_at_peace() -> None:
    world = make_world()

    assert _tick(world) == []
    assert world.pressure.last_bands == {}


def test_tick_drops_expired_offers_and_subsidies() -> None:
    world = make_world()
    war = add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    from app.engine.pressure.forcers import open_mediation

    open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)
    world.clock.turn += 10

    _tick(world)

    assert world.pressure.mediation_offers == []


def test_time_phase_updates_stalemate_counters_and_files_bands() -> None:
    world = make_world()
    war = add_war(world)
    context = PhaseContext(
        scenario=SCENARIO,
        orders=(),
        rng=_rng(),
        resolved_outcomes={},
        recorded_answers={},
    )

    TimePhase().run(world, context)
    TimePhase().run(world, context)

    assert world.pressure.stalemate_turns[war.id] == 1
    assert PLAYER in world.pressure.last_bands
