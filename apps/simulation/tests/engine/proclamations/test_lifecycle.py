from app.engine.proclamations.lifecycle import (
    apply_proclamation_enactment,
    tick_active_proclamation_turn,
)
from strategy_contracts.proclamation import (
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
)
from tests.engine.diplomacy.builders import make_world


def test_enactment_creates_active_proclamation() -> None:
    world = make_world()
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.EMERGENCY_TAXATION,
        burden=ProclamationBurden.MODERATE,
        legal_summary="Levy merchant gold.",
    )
    active = apply_proclamation_enactment(world, draft, is_rescinding=False)
    assert world.active_proclamation is not None
    assert world.active_proclamation.remaining_turns == 4
    assert active.domain is ProclamationDomain.EMERGENCY_TAXATION


def test_rescinding_adds_ten_unrest_to_provinces() -> None:
    world = make_world()
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.POPULAR_RELIEF,
        burden=ProclamationBurden.LIGHT,
        legal_summary="Grain distribution.",
    )
    apply_proclamation_enactment(world, draft, is_rescinding=False)
    player_id = next(k for k, f in world.factions.items() if f.is_player)
    player_region_keys = [
        r_id for r_id, r in world.regions.items() if r.owner_id == player_id
    ]
    initial_unrest = world.regions[player_region_keys[0]].unrest

    draft2 = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.LIGHT,
        legal_summary="War draft.",
    )
    apply_proclamation_enactment(world, draft2, is_rescinding=True)
    # 10 from rescinding penalty + 3 from light martial levies (2.5 rounds away from zero)
    assert world.regions[player_region_keys[0]].unrest == initial_unrest + 13


def test_tick_decrements_remaining_turns_and_clears_on_zero() -> None:
    world = make_world()
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.LIGHT,
        legal_summary="Levy.",
    )
    apply_proclamation_enactment(world, draft, is_rescinding=False)
    for _ in range(4):
        tick_active_proclamation_turn(world)
    assert world.active_proclamation is None


def _player_id(world) -> str:
    return next(k for k, f in world.factions.items() if f.is_player)


def _draft(domain: ProclamationDomain, burden: ProclamationBurden):
    return ProclamationDraft(
        is_recognized=True, domain=domain, burden=burden, legal_summary="Decree."
    )


def test_martial_levies_add_manpower_across_the_players_regions() -> None:
    world = make_world()
    player_id = _player_id(world)
    owned = sorted(
        r for r, region in world.regions.items() if region.owner_id == player_id
    )
    before = {r: world.regions[r].manpower for r in owned}

    apply_proclamation_enactment(
        world, _draft(ProclamationDomain.MARTIAL_LEVIES, ProclamationBurden.MODERATE)
    )

    gained = sum(world.regions[r].manpower - before[r] for r in owned)
    assert gained == 200
    assert all(world.regions[r].manpower >= before[r] for r in owned)


def test_a_negative_manpower_effect_never_drops_below_zero() -> None:
    world = make_world()
    player_id = _player_id(world)
    for region in world.regions.values():
        if region.owner_id == player_id:
            region.manpower = 1
    world.active_proclamation = None

    from app.engine.proclamations.lifecycle import _apply_manpower_delta

    _apply_manpower_delta(world, player_id, -500)

    assert all(
        region.manpower == 0
        for region in world.regions.values()
        if region.owner_id == player_id
    )


def test_religious_orthodoxy_lifts_player_army_morale_within_bounds() -> None:
    world = make_world()
    player_id = _player_id(world)
    armies = [a for a in world.armies.values() if a.owner_id == player_id]
    assert armies
    armies[0].morale = 95
    others_before = {
        a.id: a.morale for a in world.armies.values() if a.owner_id != player_id
    }

    apply_proclamation_enactment(
        world,
        _draft(ProclamationDomain.RELIGIOUS_ORTHODOXY, ProclamationBurden.MODERATE),
    )

    assert armies[0].morale == 100
    assert {
        a.id: a.morale for a in world.armies.values() if a.owner_id != player_id
    } == others_before


def test_the_active_edict_records_whole_number_modifiers() -> None:
    world = make_world()

    active = apply_proclamation_enactment(
        world,
        _draft(ProclamationDomain.EMERGENCY_TAXATION, ProclamationBurden.SEVERE),
    )

    assert all(type(value) is int for value in active.ongoing_modifiers.values())
    assert active.ongoing_modifiers["tax_percent_points"] == 26
