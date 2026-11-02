import pytest
from app.exceptions.base import SimulationServiceError
from app.models.battle_intelligence import (
    Confidence,
    MissionTarget,
    ReconReport,
    StrengthInterval,
)
from app.models.world_battle import StandingPlan
from app.models.world_state import WorldState
from strategy_contracts.battle import Tactic
from strategy_contracts.enums import TroopType
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import (
    ALLY,
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    start_battle,
)

FORBIDDEN_FIELDS = (
    "987",
    "7654321",
    "cavalry",
    '"rng"',
    '"seed"',
    '"intent_id"',
    '"deception_expires_exchange"',
    '"command"',
    '"has_leaked"',
    '"is_useful"',
)


def observed_report() -> ReconReport:
    return ReconReport(
        id="report_visible",
        battle_id=BATTLE_ID,
        observer_faction_id=ATTACKER,
        subject_faction_id=DEFENDER,
        mission_id="mission_visible",
        target=MissionTarget.COMPOSITION,
        observed_turn=0,
        observed_exchange=1,
        available_from_wave=2,
        strength=StrengthInterval(minimum=90, maximum=110),
        composition={TroopType.INFANTRY: 100},
        confidence=Confidence.HIGH,
    )


def private_fixture() -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture(50, 987, casualty_rate_percent=0)
    start_battle(world, scenario)
    world.armies["army_b"].troops = {TroopType.CAVALRY: 987}
    world.factions[DEFENDER].treasury = 7654321
    world.battles[0].contingents[DEFENDER].plan = StandingPlan(tactic=Tactic.PRESS)
    world.recon_reports["report_visible"] = observed_report()
    world.battles[0].report_ids.append("report_visible")
    return world, scenario


def test_projection_allowlists_own_information_and_delays_other_reports() -> None:
    from app.engine.battles.views import intent_briefing, project_battle

    world, scenario = private_fixture()
    before = world.model_dump()
    hidden = project_battle(world, BATTLE_ID, ATTACKER, scenario)
    assert hidden.opponents[0].reports == []
    serialized = hidden.model_dump_json()
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in serialized
    assert project_battle(world, BATTLE_ID, ATTACKER, scenario) == hidden
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    assert briefing.battle == hidden
    assert '"rng"' not in briefing.model_dump_json()
    assert "7654321" not in briefing.model_dump_json()
    assert world.model_dump() == before


def test_visible_report_remains_a_timestamped_observation_after_truth_changes() -> None:
    from app.engine.battles.views import project_battle

    world, scenario = private_fixture()
    world.battles[0].exchanges_used = 1
    world.battles[0].total_exchanges = 1
    visible = project_battle(world, BATTLE_ID, ATTACKER, scenario)
    assert visible.opponents[0].reports == [observed_report()]
    assert visible.opponents[0].strength == StrengthInterval(minimum=90, maximum=110)
    world.armies["army_b"].troops = {TroopType.CAVALRY: 7}
    assert project_battle(world, BATTLE_ID, ATTACKER, scenario).opponents[0].reports[
        0
    ].composition == {TroopType.INFANTRY: 100}


def test_nonparticipant_cannot_read_battle_or_use_unaware_tactic() -> None:
    from app.engine.battles.views import project_battle, validate_observed_plan

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    with pytest.raises(SimulationServiceError, match="unavailable"):
        project_battle(world, BATTLE_ID, ALLY, scenario)
    with pytest.raises(
        SimulationServiceError, match="flank requirements are unavailable"
    ):
        validate_observed_plan(
            world, BATTLE_ID, ATTACKER, StandingPlan(tactic=Tactic.FLANK), scenario
        )


def test_departed_contingent_has_no_legal_commands() -> None:
    from app.engine.battles.views import project_battle
    from app.models.world_battle import ContingentStatus

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.battles[0].contingents[ATTACKER].status = ContingentStatus.WITHDRAWN

    assert project_battle(world, BATTLE_ID, ATTACKER, scenario).legal_commands == []


def test_projection_reports_the_terrain_frontage_limit() -> None:
    from app.engine.battles.views import project_battle

    world, scenario = private_fixture()
    view = project_battle(world, BATTLE_ID, ATTACKER, scenario)

    assert view.frontage == scenario.tuning.battle.frontage[view.terrain]
    assert view.frontage > 0


def test_own_contingent_shows_active_and_reserve_but_not_the_opponent_split() -> None:
    from app.engine.battles.views import project_battle

    world, scenario = private_fixture()
    own = project_battle(world, BATTLE_ID, ATTACKER, scenario).own_contingent
    deployment = next(iter(world.battles[0].contingents[ATTACKER].deployments.values()))

    assert own.active == {k: v for k, v in deployment.active.items() if v}
    assert own.reserve == {k: v for k, v in deployment.reserve.items() if v}
    assert sum(own.active.values()) + sum(own.reserve.values()) == sum(
        own.troops.values()
    )
    dumped = project_battle(world, BATTLE_ID, ATTACKER, scenario).model_dump_json()
    assert dumped.count('"active"') == 1
