import pytest
from app.exceptions.base import SimulationServiceError
from app.models.battle_intelligence import (
    CaptureDecision,
    MissionTarget,
    PreparationHint,
    ScoutCapture,
)
from app.models.world_battle import BattleOutcome, BattleStatus
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    start_battle,
)


def capture_fixture() -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    capture = ScoutCapture(
        id="capture_test",
        battle_id=BATTLE_ID,
        mission_id="mission_test",
        captor_faction_id=DEFENDER,
        origin_faction_id=ATTACKER,
        captured_turn=0,
        captured_exchange=1,
        expires_turn=1,
        mission_target=MissionTarget.RESERVES,
        briefing_hint=PreparationHint.ADVANCING,
    )
    world.scout_captures[capture.id] = capture
    world.battles[0].capture_ids = [capture.id]
    world.battles[0].contingents[ATTACKER].recon_penalty = 10
    return world, scenario


def test_capture_expiry_uses_campaign_clock_even_after_battle_ends() -> None:
    from app.engine.battles.captures import expire_captures

    world, scenario = capture_fixture()
    world.battles[0].status = BattleStatus.RESOLVED
    world.battles[0].outcome = BattleOutcome.DEFENDER_VICTORY
    assert expire_captures(world, scenario).captures == {}
    world.clock.turn = 1
    result = expire_captures(world, scenario)
    assert result.captures["capture_test"].status.value == "released"
    assert result.battles[BATTLE_ID].contingents[ATTACKER].recon_penalty == 0
    assert world.scout_captures["capture_test"].status.value == "detained"


def test_free_default_detention_allows_only_one_paid_extension() -> None:
    from app.engine.battles.captures import resolve_capture_decision

    world, scenario = capture_fixture()
    result = resolve_capture_decision(
        world, "capture_test", DEFENDER, CaptureDecision.DETAIN, scenario
    )
    assert result.capture.expires_turn == 2
    assert result.capture.has_extended and result.capture.has_decided
    assert result.report is None
    world.scout_captures["capture_test"] = result.capture
    with pytest.raises(SimulationServiceError, match="unavailable"):
        resolve_capture_decision(
            world, "capture_test", DEFENDER, CaptureDecision.DETAIN, scenario
        )


def test_interrogation_leaks_assigned_information_once_and_has_mistaken_branch() -> (
    None
):
    from app.engine.battles.captures import resolve_capture_decision

    world, scenario = capture_fixture()
    scenario.tuning.battle.interrogation_useful_percent = 100
    result = resolve_capture_decision(
        world, "capture_test", DEFENDER, CaptureDecision.INTERROGATE, scenario
    )
    assert result.report.target == MissionTarget.RESERVES
    assert result.report.preparation_hint == PreparationHint.ADVANCING
    assert result.capture.has_leaked and result.capture.has_decided
    world.scout_captures["capture_test"] = result.capture
    with pytest.raises(SimulationServiceError):
        resolve_capture_decision(
            world, "capture_test", DEFENDER, CaptureDecision.INTERROGATE, scenario
        )
    world, scenario = capture_fixture()
    scenario.tuning.battle.interrogation_useful_percent = 0
    mistaken = resolve_capture_decision(
        world, "capture_test", DEFENDER, CaptureDecision.INTERROGATE, scenario
    )
    assert mistaken.report.preparation_hint != PreparationHint.ADVANCING


def test_release_is_private_and_unauthorized_decisions_are_rejected() -> None:
    from app.engine.battles.captures import resolve_capture_decision

    world, scenario = capture_fixture()
    with pytest.raises(SimulationServiceError, match="unavailable"):
        resolve_capture_decision(
            world, "capture_test", ATTACKER, CaptureDecision.RELEASE, scenario
        )
    result = resolve_capture_decision(
        world, "capture_test", DEFENDER, CaptureDecision.RELEASE, scenario
    )
    assert result.capture.status.value == "released"
    assert result.report is None
    assert sum(world.armies["army_a"].troops.values()) == 1000


def test_capture_penalties_cap_and_release_restores_from_remaining_active_records() -> (
    None
):
    from app.engine.battles.captures import expire_captures, refresh_penalties

    world, scenario = capture_fixture()
    for index in range(1, 5):
        record = world.scout_captures["capture_test"].model_copy(
            update={"id": f"capture_{index}", "expires_turn": 2}
        )
        world.scout_captures[record.id] = record
    refresh_penalties(world, world.battles[0], scenario)
    assert world.battles[0].contingents[ATTACKER].recon_penalty == 30
    world.clock.turn = 1
    expired = expire_captures(world, scenario)
    assert expired.battles[BATTLE_ID].contingents[ATTACKER].recon_penalty == 30
    world.clock.turn = 2
    expired = expire_captures(world, scenario)
    assert expired.battles[BATTLE_ID].contingents[ATTACKER].recon_penalty == 0


def test_capture_release_command_updates_penalty_and_owned_delta_without_losses() -> (
    None
):
    from app.models.battle_command import CaptureDecisionCommand

    from tests.engine.battles.builders import command, exchange

    world, scenario = capture_fixture()
    scenario.tuning.battle.casualty_rate_percent = 0
    result = exchange(
        world,
        scenario,
        [
            command(
                CaptureDecisionCommand(
                    faction_id=DEFENDER,
                    battle_id=BATTLE_ID,
                    capture_id="capture_test",
                    decision=CaptureDecision.RELEASE,
                )
            )
        ],
    )
    assert result.delta.scout_captures["capture_test"].status.value == "released"
    assert result.delta.battle.contingents[ATTACKER].recon_penalty == 0
    assert all(
        not row.combat_losses and not row.captives for row in result.receipt.accounting
    )
    assert world.scout_captures["capture_test"].status.value == "detained"
