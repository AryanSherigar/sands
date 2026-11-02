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
    # 10 from rescinding penalty + 2 from light martial levies immediate unrest
    assert world.regions[player_region_keys[0]].unrest == initial_unrest + 12


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
