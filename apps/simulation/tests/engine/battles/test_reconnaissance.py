import pytest
from app.models.battle_command import AcceptedCommand, DeceiveCommand, ReconCommand
from app.models.battle_intelligence import MissionTarget, ScoutCapture, ScoutMission
from strategy_contracts.enums import TroopType

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    command,
    exchange,
    start_battle,
)


def mission(identity: str = "mission_test") -> ScoutMission:
    return ScoutMission(
        id=identity,
        battle_id=BATTLE_ID,
        observer_faction_id=ATTACKER,
        subject_faction_id=DEFENDER,
        target=MissionTarget.COMPOSITION,
        execution_turn=0,
        execution_wave=1,
    )


def test_professional_rating_is_independent_of_cavalry_and_clamped_after_captures() -> (
    None
):
    from app.engine.battles.reconnaissance import professional_rating

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    assert (
        professional_rating(
            world.battles[0].contingents[ATTACKER], scenario.tuning.battle
        )
        == 50
    )
    world.armies["army_a"].troops = {TroopType.CAVALRY: 100000}
    contingent = world.battles[0].contingents[ATTACKER]
    assert professional_rating(contingent, scenario.tuning.battle) == 50
    contingent.recon_penalty = 100
    assert professional_rating(contingent, scenario.tuning.battle) == 0


def test_seed_matrix_contains_capture_exact_observation_and_ordinary_mistake() -> None:
    from app.engine.battles.reconnaissance import resolve_recon

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    before = world.model_dump()
    results = [
        resolve_recon(world, mission(str(seed)), scenario) for seed in range(200)
    ]
    assert world.model_dump() == before
    assert any(result.capture and result.report is None for result in results)
    assert any(
        result.report and result.report.composition == {TroopType.INFANTRY: 1000}
        for result in results
    )
    assert any(
        result.report
        and result.report.strength.minimum + result.report.strength.maximum != 2000
        for result in results
    )
    assert all(
        result.report.available_from_wave == 2 for result in results if result.report
    )
    assert results == [
        resolve_recon(world, mission(str(seed)), scenario) for seed in range(200)
    ]


def test_deception_consumes_next_mission_and_can_create_confidently_wrong_hint() -> (
    None
):
    from app.engine.battles.reconnaissance import resolve_recon

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    subject = world.battles[0].contingents[DEFENDER]
    subject.deception_expires_exchange = 1
    results = []
    for seed in range(100):
        candidate = mission(str(seed))
        candidate.target = MissionTarget.PREPARATION
        results.append(resolve_recon(world, candidate, scenario))
    assert any(
        result.report
        and result.report.confidence.value == "high"
        and result.report.preparation_hint.value != "holding"
        for result in results
    )
    assert all(result.has_consumed_deception for result in results)


def test_exchange_support_commands_are_owned_deltas_and_reports_wait_for_next_wave() -> (
    None
):
    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    before = world.model_dump()
    commands = [
        command(
            ReconCommand(
                faction_id=ATTACKER,
                battle_id=BATTLE_ID,
                subject_faction_id=DEFENDER,
                target=MissionTarget.COMPOSITION,
            )
        ),
        command(
            DeceiveCommand(faction_id=DEFENDER, battle_id=BATTLE_ID), identity="deceive"
        ),
    ]
    result = exchange(world, scenario, commands)
    assert world.model_dump() == before
    assert len(result.delta.scout_missions) == 1
    assert len(result.delta.recon_reports) + len(result.delta.scout_captures) == 1
    assert result.world.counters == world.counters
    assert all(
        accepted.status.value == "applied" for accepted in result.delta.command_updates
    )
    assert exchange(world, scenario, list(reversed(commands))) == result


def test_recon_rejects_own_or_unknown_subject_without_leaking_state() -> None:
    from app.engine.battles.reconnaissance import resolve_recon
    from app.exceptions.base import SimulationServiceError

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    candidate = mission()
    candidate.subject_faction_id = ATTACKER
    with pytest.raises(SimulationServiceError, match="opposing contingent"):
        resolve_recon(world, candidate, scenario)


def test_simultaneous_captures_penalize_both_sides_without_soldier_losses() -> None:
    from app.models.battle_intelligence import ScoutCaptureStatus

    world, scenario = battle_fixture(casualty_rate_percent=0)
    scenario.tuning.battle.capture_min_percent = 100
    scenario.tuning.battle.capture_max_percent = 100
    start_battle(world, scenario)
    commands = opposing_commands(MissionTarget.COMPOSITION)
    before = {identity: army.troops.copy() for identity, army in world.armies.items()}
    result = exchange(world, scenario, commands)
    assert len(result.delta.scout_captures) == 2
    assert not result.delta.recon_reports
    assert all(
        capture.status == ScoutCaptureStatus.DETAINED
        for capture in result.delta.scout_captures.values()
    )
    assert [
        contingent.recon_penalty
        for contingent in result.delta.battle.contingents.values()
    ] == [10, 10]
    assert {
        identity: army.troops for identity, army in result.world.armies.items()
    } == before


def test_simultaneous_deception_freezes_each_scout_briefing_before_consumption() -> (
    None
):
    from app.models.battle_intelligence import PreparationHint

    world, scenario = battle_fixture(
        casualty_rate_percent=0, capture_min_percent=100, capture_max_percent=100
    )
    start_battle(world, scenario)
    commands = opposing_commands(MissionTarget.PREPARATION)
    commands.extend(
        command(
            DeceiveCommand(faction_id=faction, battle_id=BATTLE_ID),
            identity=f"deceive_{faction}",
        )
        for faction in (ATTACKER, DEFENDER)
    )
    result = exchange(world, scenario, commands)
    assert [
        capture.briefing_hint for capture in result.delta.scout_captures.values()
    ] == [PreparationHint.ADVANCING, PreparationHint.ADVANCING]


def test_expired_capture_does_not_penalize_next_campaign_recon() -> None:
    world, scenario = battle_fixture(
        casualty_rate_percent=0, capture_min_percent=0, capture_max_percent=0
    )
    start_battle(world, scenario)
    world.clock.turn = 1
    world.battles[0].current_turn = 1
    captured = expired_capture()
    world.scout_captures[captured.id] = captured
    world.battles[0].contingents[ATTACKER].recon_penalty = 10
    accepted = command(
        ReconCommand(
            faction_id=ATTACKER,
            battle_id=BATTLE_ID,
            subject_faction_id=DEFENDER,
            target=MissionTarget.COMPOSITION,
        )
    )
    accepted.execution_turn = 1
    for seed in range(100):
        world.rng.seed = seed
        clean = world.model_copy(deep=True)
        clean.battles[0].contingents[ATTACKER].recon_penalty = 0
        assert (
            exchange(world, scenario, [accepted]).delta.recon_reports
            == exchange(clean, scenario, [accepted]).delta.recon_reports
        )


def opposing_commands(target: MissionTarget) -> list[AcceptedCommand]:
    return [
        command(
            ReconCommand(
                faction_id=faction,
                battle_id=BATTLE_ID,
                subject_faction_id=subject,
                target=target,
            ),
            identity=faction,
        )
        for faction, subject in ((ATTACKER, DEFENDER), (DEFENDER, ATTACKER))
    ]


def expired_capture() -> ScoutCapture:
    return ScoutCapture(
        id="old_capture",
        battle_id=BATTLE_ID,
        mission_id="old_mission",
        captor_faction_id=DEFENDER,
        origin_faction_id=ATTACKER,
        captured_turn=0,
        captured_exchange=1,
        expires_turn=1,
        mission_target=MissionTarget.COMPOSITION,
    )
