import pytest
from app.engine.diplomacy.fabrication import (
    exposure_chance_percent,
    start_forgery,
    tick_forgeries,
)
from app.engine.diplomacy.grounds import grant_ground, is_usable
from app.engine.rng import derive_rng
from app.exceptions.command_exceptions import CommandError
from app.models.orders import FabricateClaimOrder
from strategy_contracts.diplomacy import GroundKind

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    queue_npc_order,
    set_traits,
)

FORGER = WRATHFUL_RIVAL
TARGET = CAUTIOUS_RIVAL
REGION = "elmstead"
TUNING = SCENARIO.tuning.diplomacy


class AlwaysExposed:
    def fork(self, *keys):
        return self

    def roll_range(self, low: int, high: int) -> int:
        return low


def _order() -> FabricateClaimOrder:
    return FabricateClaimOrder(
        faction_id=FORGER, target_faction_id=TARGET, region_id=REGION
    )


def _forged_world():
    world = make_world()
    start_forgery(world, SCENARIO, _order())
    return world


def test_forgery_is_unusable_until_matured() -> None:
    world = _forged_world()
    set_traits(world, FORGER, [])
    ground = world.grounds[0]

    world.clock.turn = TUNING.fabrication_turns - 1
    assert not is_usable(world, SCENARIO, ground)
    world.clock.turn = TUNING.fabrication_turns
    assert is_usable(world, SCENARIO, ground)


def test_forgery_is_marked_forged_with_zero_suspicion() -> None:
    ground = _forged_world().grounds[0]

    assert (ground.is_forged, ground.suspect_level) == (True, 0)
    assert ground.strength == TUNING.fabricated_claim_strength


def test_suspect_rises_each_tick_when_nobody_is_cunning() -> None:
    world = _forged_world()
    for faction_id in (PLAYER, TARGET):
        set_traits(world, faction_id, ["honorable"])
    rng = derive_rng(world.rng.seed, 1, "time")

    tick_forgeries(world, SCENARIO, rng)
    tick_forgeries(world, SCENARIO, rng)

    assert world.grounds[0].suspect_level == 2 * TUNING.suspect_per_turn


def test_exposure_chance_scales_and_is_capped() -> None:
    assert exposure_chance_percent(15, 3, TUNING) == 11
    assert exposure_chance_percent(100, 3, TUNING) == 75
    assert (
        exposure_chance_percent(1000, 3, TUNING) == TUNING.exposure_chance_cap_percent
    )


def test_exposure_is_deterministic_for_a_seed() -> None:
    def run():
        world = _forged_world()
        world.grounds[0].suspect_level = 100
        events = tick_forgeries(world, SCENARIO, derive_rng(7, 1, "time"))
        return [event.kind for event in events], world.model_dump()

    assert run() == run()


def test_exposure_costs_reputation_and_grants_the_rival_a_ground() -> None:
    world = _forged_world()
    world.grounds[0].suspect_level = 100
    before = world.factions[FORGER].reputation

    events = tick_forgeries(world, SCENARIO, AlwaysExposed())

    assert [event.kind for event in events] == ["forgery_exposed"]
    assert world.factions[FORGER].reputation == before - TUNING.exposure_reputation_cost
    assert [(g.kind, g.target_faction_id) for g in world.grounds] == [
        (GroundKind.BROKEN_PROMISE, FORGER)
    ]


def test_non_cunning_rival_never_exposes() -> None:
    world = _forged_world()
    world.grounds[0].suspect_level = 1000
    for faction_id in (PLAYER, TARGET):
        set_traits(world, faction_id, ["honorable"])

    events = tick_forgeries(world, SCENARIO, AlwaysExposed())

    assert events == []
    assert world.grounds[0].is_forged


def test_forging_over_an_existing_claim_is_rejected() -> None:
    world = make_world()
    grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=FORGER,
        target_faction_id=TARGET,
        region_id=REGION,
    )

    with pytest.raises(CommandError) as raised:
        queue_npc_order(world, SCENARIO, _order())

    assert raised.value.code == "already_claimed"


def test_phase_applies_a_queued_forgery_order() -> None:
    from app.engine.diplomacy.phase import DiplomacyPhase

    from tests.engine.diplomacy.builders import run_phase

    world = queue_npc_order(make_world(), SCENARIO, _order())

    result = run_phase(DiplomacyPhase(), world)

    assert [ground.is_forged for ground in result.world.grounds] == [True]
    assert "forgery_started" in [event.kind for event in result.events]
