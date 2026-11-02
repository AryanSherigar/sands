from app.engine.judgments.eligibility import eligible_subjects
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.judgment import JudgmentSubjectKind

from tests.engine.judgments.builders import (
    CAPTIVE_ID,
    GOVERNOR_ID,
    GOVERNOR_REGION,
    OTHER_REGION,
    PLAYER,
    PLAYER_LEADER,
    RIVAL,
    TURN,
    judgment_scenario,
    judgment_world,
    mercy_hostage,
    uprising_event,
)


def _subjects(world, events=()):
    return eligible_subjects(world, judgment_scenario(), list(events))


def test_a_character_prisoner_held_by_the_player_is_eligible() -> None:
    [pending] = _subjects(judgment_world())
    assert pending.subject_kind is JudgmentSubjectKind.CAPTIVE
    assert pending.subject_id == CAPTIVE_ID
    assert pending.accused_faction_id == RIVAL
    assert pending.cooldown_until_turn == TURN + 6


def test_troop_prisoners_the_players_own_ruler_and_enemy_held_prisoners_are_not() -> (
    None
):
    world = judgment_world()
    world.prisoners = [
        PrisonerState(
            id="troops",
            held_by_id=PLAYER,
            origin_faction_id=RIVAL,
            kind=PrisonerKind.TROOPS,
            troop_count=5,
            origin_battle_id="b1",
            troops_by_type={"infantry": 5},
        ),
        PrisonerState(
            id="own_ruler",
            held_by_id=RIVAL,
            origin_faction_id=PLAYER,
            kind=PrisonerKind.CHARACTER,
            character_id=PLAYER_LEADER,
        ),
        PrisonerState(
            id="held_by_ai",
            held_by_id=RIVAL,
            origin_faction_id=PLAYER,
            kind=PrisonerKind.CHARACTER,
            character_id="ser_other",
        ),
    ]
    assert _subjects(world) == []


def test_a_hostage_at_mercy_held_by_the_player_is_eligible() -> None:
    world = judgment_world()
    world.prisoners = []
    world.peace.hostages = [mercy_hostage()]
    [pending] = _subjects(world)
    assert (pending.subject_id, pending.accused_faction_id) == ("hostage_1", RIVAL)
    world.peace.hostages = [mercy_hostage(is_at_mercy=False)]
    assert _subjects(world) == []


def test_a_judged_captive_is_not_judged_again_while_kept_in_custody() -> None:
    world = judgment_world()
    world.judgment_cooldowns[CAPTIVE_ID] = TURN - 3
    assert _subjects(world) == []


def test_an_expired_sentence_makes_the_captive_eligible_again() -> None:
    world = judgment_world()
    world.judgment_cooldowns[CAPTIVE_ID] = TURN - 3
    world.prisoners[0].sentence_ends_turn = TURN
    assert [item.subject_id for item in _subjects(world)] == [CAPTIVE_ID]
    world.prisoners[0].sentence_ends_turn = TURN + 1
    assert _subjects(world) == []


def test_a_governor_in_a_region_with_a_crushed_uprising_is_eligible() -> None:
    world = judgment_world()
    world.prisoners = []
    [pending] = _subjects(world, [uprising_event("uprising_crushed")])
    assert pending.subject_kind is JudgmentSubjectKind.GOVERNOR
    assert pending.subject_id == GOVERNOR_ID
    assert pending.accused_faction_id == PLAYER
    assert pending.trigger_event == "uprising_crushed"


def test_flipped_and_newly_armed_uprisings_also_qualify() -> None:
    world = judgment_world()
    world.prisoners = []
    flipped = [uprising_event("uprising_flipped")]
    armed = [uprising_event("uprising_stage_changed", stage_after="armed")]
    assert len(_subjects(world, flipped)) == 1
    assert len(_subjects(world, armed)) == 1


def test_a_governor_is_not_eligible_without_a_qualifying_uprising() -> None:
    world = judgment_world()
    world.prisoners = []
    assert _subjects(world) == []
    riot = [uprising_event("uprising_stage_changed", stage_after="riot")]
    assert _subjects(world, riot) == []
    started = [uprising_event("uprising_started")]
    assert _subjects(world, started) == []


def test_uprisings_of_other_factions_or_governorless_regions_do_not_qualify() -> None:
    world = judgment_world()
    world.prisoners = []
    world.regions[OTHER_REGION].governor_id = None
    foreign = uprising_event("uprising_crushed", faction_id=RIVAL)
    governorless = uprising_event("uprising_crushed", region_id=OTHER_REGION)
    assert _subjects(world, [foreign, governorless]) == []


def test_a_governor_cooldown_blocks_a_second_judgment_until_it_expires() -> None:
    world = judgment_world()
    world.prisoners = []
    event = uprising_event("uprising_crushed")
    world.judgment_cooldowns[GOVERNOR_ID] = TURN + 1
    assert _subjects(world, [event]) == []
    world.judgment_cooldowns[GOVERNOR_ID] = TURN
    assert len(_subjects(world, [event])) == 1


def test_subjects_are_sorted_captives_first_then_by_id() -> None:
    world = judgment_world()
    world.prisoners.append(
        world.prisoners[0].model_copy(
            update={"id": "captive_0", "character_id": "ser_zed"}
        )
    )
    events = [uprising_event("uprising_crushed", region_id=GOVERNOR_REGION)]
    assert [item.subject_id for item in _subjects(world, events)] == [
        "captive_0",
        CAPTIVE_ID,
        GOVERNOR_ID,
    ]
