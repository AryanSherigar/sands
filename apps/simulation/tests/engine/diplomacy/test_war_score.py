from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.phase import TimePhase
from app.engine.diplomacy.war_score import goal_slots, tally_war_scores
from app.models.world_battle import (
    BattleContingent,
    BattleOutcome,
    BattleSide,
    BattleState,
    BattleStatus,
)
from app.models.world_diplomacy import PrisonerKind, PrisonerState, WarSide, WarState
from app.models.world_events import PhaseName
from app.models.world_region import OccupationState
from strategy_contracts.diplomacy import GroundKind, ScoreSource
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    run_phase,
    set_traits,
)

ATTACKER = WRATHFUL_RIVAL
DEFENDER = PLAYER
TUNING = SCENARIO.tuning.diplomacy


def _world_at_war():
    world = make_world()
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=ATTACKER,
            defender_id=DEFENDER,
            participant_ids=[ATTACKER, DEFENDER],
            started_turn=0,
        )
    )
    return world


def _battle(
    world,
    battle_id: str = "battle_1",
    outcome: BattleOutcome = BattleOutcome.ATTACKER_VICTORY,
    defender: str = DEFENDER,
    defender_army: str = "army_ashford_1",
) -> BattleState:
    battle = BattleState(
        id=battle_id,
        region_id="brennmoor",
        attacker_army_ids=["army_dunwick_1"],
        defender_army_ids=[defender_army],
        attacker_lead_faction_id=ATTACKER,
        defender_lead_faction_id=defender,
        status=BattleStatus.RESOLVED,
        outcome=outcome,
        contingents={
            ATTACKER: BattleContingent(
                faction_id=ATTACKER,
                side=BattleSide.ATTACKER,
                army_ids=["army_dunwick_1"],
                entry_troops=330,
            ),
            defender: BattleContingent(
                faction_id=defender,
                side=BattleSide.DEFENDER,
                army_ids=[defender_army],
                entry_troops=400,
            ),
        },
    )
    world.battles.append(battle)
    return battle


def test_victory_scores_fifteen_and_marks_battle_scored() -> None:
    world = _world_at_war()
    _battle(world)

    events = tally_war_scores(world, SCENARIO)

    war = world.wars[0]
    assert war.war_score_attacker == TUNING.score_weights[ScoreSource.BATTLE_WON]
    assert war.scored_battle_ids == ["battle_1"]
    assert [event.kind for event in events] == ["war_score_changed"]


def test_defender_victory_scores_for_the_defender() -> None:
    world = _world_at_war()
    _battle(world, outcome=BattleOutcome.DEFENDER_VICTORY)

    tally_war_scores(world, SCENARIO)

    assert (world.wars[0].war_score_attacker, world.wars[0].war_score_defender) == (
        0,
        15,
    )


def test_same_battle_never_scored_twice() -> None:
    world = _world_at_war()
    _battle(world)

    tally_war_scores(world, SCENARIO)
    events = tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == 15
    assert events == []


def test_destroyed_army_adds_ten() -> None:
    world = _world_at_war()
    world.armies["army_ashford_1"].troops = {}
    _battle(world)

    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == 25


def _hold(world, troops: int, prisoner_id: str = "prisoners_1") -> None:
    world.prisoners.append(
        PrisonerState(
            id=prisoner_id,
            held_by_id=ATTACKER,
            origin_faction_id=DEFENDER,
            kind=PrisonerKind.TROOPS,
            troop_count=troops,
            origin_battle_id="battle_x",
            troops_by_type={TroopType.INFANTRY: troops},
        )
    )


def _prisoner_score(troops: int) -> int:
    world = _world_at_war()
    _hold(world, troops)
    tally_war_scores(world, SCENARIO)
    return world.wars[0].war_score_attacker


def test_legacy_ruleset_scores_prisoners_by_fifty_and_they_fall_when_released() -> None:
    world = _world_at_war()
    world.peace_ruleset = 1
    _hold(world, 100)
    tally_war_scores(world, SCENARIO)
    assert world.wars[0].war_score_attacker == 2

    world.prisoners = []
    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == 0


def test_a_handful_of_captives_score_nothing() -> None:
    assert _prisoner_score(1) == 0
    assert _prisoner_score(2) == 0
    assert _prisoner_score(50) == 0


def test_a_thousand_captives_matter_and_ten_thousand_matter_more() -> None:
    thousand = _prisoner_score(1000)
    ten_thousand = _prisoner_score(10000)

    assert thousand > 0
    assert ten_thousand > thousand


def test_ten_times_the_captives_is_far_less_than_ten_times_the_score() -> None:
    assert _prisoner_score(10000) < 3 * _prisoner_score(1000)


def test_captive_score_never_passes_its_ceiling() -> None:
    assert _prisoner_score(10_000_000) <= TUNING.prisoner_score_ceiling


def test_captive_score_never_falls_as_captives_grow() -> None:
    scores = [_prisoner_score(count) for count in (0, 10, 100, 500, 1000, 5000, 50000)]

    assert scores == sorted(scores)


def test_released_captives_stop_scoring_under_the_curve() -> None:
    world = _world_at_war()
    _hold(world, 2000)
    tally_war_scores(world, SCENARIO)
    assert world.wars[0].war_score_attacker > 0

    world.prisoners = []
    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == 0


def test_score_is_capped_at_one_hundred() -> None:
    world = _world_at_war()
    world.wars[0].battle_points_attacker = 99
    _battle(world)

    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == TUNING.war_score_cap


def test_battle_between_factions_not_at_war_is_ignored() -> None:
    world = _world_at_war()
    _battle(world, defender=CAUTIOUS_RIVAL, defender_army="army_carrow_1")

    events = tally_war_scores(world, SCENARIO)

    assert (events, world.wars[0].scored_battle_ids) == ([], [])


def test_goal_slots_unlock_at_forty_and_seventy() -> None:
    assert [goal_slots(score, TUNING) for score in (0, 39, 40, 70)] == [1, 1, 2, 3]


def test_time_phase_expires_faded_grounds() -> None:
    world = make_world()
    world.succession_ruleset = 0
    set_traits(world, ATTACKER, [])
    ground = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=ATTACKER,
        target_faction_id=DEFENDER,
        region_id="brennmoor",
        strength=2,
    )
    world.clock.turn = 1

    result = run_phase(TimePhase(), world)

    assert result.world.grounds == []
    assert [(event.kind, event.phase) for event in result.events] == [
        ("ground_expired", PhaseName.TIME)
    ]
    assert ground.id in result.events[0].cause.subject_ids


def test_battle_led_by_an_ally_scores_for_the_allys_side() -> None:
    world = _world_at_war()
    war = world.wars[0]
    war.participant_ids.append(CAUTIOUS_RIVAL)
    war.side_by_faction = {
        ATTACKER: WarSide.ATTACKER,
        DEFENDER: WarSide.DEFENDER,
        CAUTIOUS_RIVAL: WarSide.DEFENDER,
    }
    _battle(
        world,
        outcome=BattleOutcome.DEFENDER_VICTORY,
        defender=CAUTIOUS_RIVAL,
        defender_army="army_carrow_1",
    )

    tally_war_scores(world, SCENARIO)

    assert war.war_score_defender == TUNING.score_weights[ScoreSource.BATTLE_WON]
    assert war.war_score_attacker == 0


def _occupy(world, region_id: str, occupier_id: str) -> None:
    world.regions[region_id].occupation = OccupationState(
        occupier_id=occupier_id, siege_progress=100
    )


def test_occupation_scores_the_occupier_side_once() -> None:
    world = _world_at_war()
    _occupy(world, "brennmoor", ATTACKER)

    tally_war_scores(world, SCENARIO)
    tally_war_scores(world, SCENARIO)

    war = world.wars[0]
    weight = TUNING.score_weights[ScoreSource.REGION_OCCUPIED]
    assert war.war_score_attacker == weight
    assert war.occupation_points_attacker == weight
    assert war.scored_region_ids == ["brennmoor"]
    assert war.war_score_defender == 0


def test_occupation_scores_for_the_defender_side_too() -> None:
    world = _world_at_war()
    _occupy(world, "dunwick", DEFENDER)

    tally_war_scores(world, SCENARIO)

    war = world.wars[0]
    assert (
        war.occupation_points_defender
        == TUNING.score_weights[ScoreSource.REGION_OCCUPIED]
    )
    assert war.war_score_attacker == 0


def test_occupying_a_third_partys_region_does_not_score() -> None:
    world = _world_at_war()
    _occupy(world, "carrow_vale", ATTACKER)

    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == 0
    assert world.wars[0].scored_region_ids == []


def test_points_survive_the_region_changing_hands() -> None:
    world = _world_at_war()
    _occupy(world, "brennmoor", ATTACKER)
    tally_war_scores(world, SCENARIO)
    region = world.regions["brennmoor"]
    region.occupation = None
    region.owner_id = ATTACKER

    tally_war_scores(world, SCENARIO)

    assert (
        world.wars[0].war_score_attacker
        == TUNING.score_weights[ScoreSource.REGION_OCCUPIED]
    )


def test_occupation_points_respect_the_war_score_cap() -> None:
    world = _world_at_war()
    world.wars[0].battle_points_attacker = TUNING.war_score_cap
    _occupy(world, "brennmoor", ATTACKER)

    tally_war_scores(world, SCENARIO)

    assert world.wars[0].war_score_attacker == TUNING.war_score_cap
