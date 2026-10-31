import pytest
from app.engine.commands.application import accept_command
from app.engine.commands.phases import CampaignEconomyPhase
from app.engine.phases import PhaseContext
from app.engine.visibility.scouting import resolve_map_scout
from app.exceptions.command_exceptions import CommandError
from app.models.orders import MapScoutOrder
from app.models.world_state import CURRENT_VISIBILITY_RULESET
from strategy_contracts.enums import Terrain
from tests.engine.movement.builders import (
    FACTION_A,
    make_map,
    make_scenario,
    make_world_for,
)


def _world_and_scenario():
    scenario = make_scenario(
        make_map(
            {"home": Terrain.PLAIN, "border": Terrain.PLAIN, "target": Terrain.PLAIN},
            [("home", "border"), ("border", "target")],
        )
    )
    world = make_world_for(
        {"home": FACTION_A, "border": "house_b", "target": "house_c"}
    )
    world.visibility_ruleset = CURRENT_VISIBILITY_RULESET
    return world, scenario


def test_map_scout_reports_deterministically_for_adjacent_target() -> None:
    world, scenario = _world_and_scenario()

    first = resolve_map_scout(world, scenario, FACTION_A, "target", "mission_1")
    second = resolve_map_scout(world, scenario, FACTION_A, "target", "mission_1")

    assert first == second
    assert first.coverage_percent >= 25


def test_map_scout_rejects_non_adjacent_target_without_report() -> None:
    world, scenario = _world_and_scenario()
    with pytest.raises(CommandError, match="map scout target unavailable"):
        resolve_map_scout(world, scenario, FACTION_A, "home", "mission_1")


def test_deceived_map_scout_cannot_claim_perfect_accuracy() -> None:
    world, scenario = _world_and_scenario()

    report = resolve_map_scout(
        world, scenario, FACTION_A, "target", "mission_1", is_deceived=True
    )

    assert report.coverage_percent < 100
    assert not report.is_accurate


def test_map_scout_command_persists_a_report() -> None:
    world, scenario = _world_and_scenario()
    accepted = accept_command(
        world,
        scenario,
        MapScoutOrder(faction_id=FACTION_A, target_region_id="target"),
        command_id="mission_1",
        operation_id="operation_1",
        actor_id="owner",
        faction_id=FACTION_A,
        expected_turn=0,
        expected_wave=0,
    )
    context = PhaseContext(
        scenario=scenario,
        orders=(),
        resolved_outcomes={},
        recorded_answers={},
        rng=None,
    )

    result = CampaignEconomyPhase().run(accepted.world, context)

    assert result.world.map_scout_reports["mission_1"].target_region_id == "target"
