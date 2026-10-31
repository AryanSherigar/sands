from uuid import UUID

from app.engine.hashing import canonical_world_json
from app.engine.letters.arming import arm_letter, letter_scene_id
from app.models.world_events import PendingLetter
from app.models.world_state import WorldState
from strategy_contracts.letters import DEFAULT_LETTER_COOLDOWN_TURNS

from tests.engine.letters.builders import (
    RIVAL,
    TURN,
    letter_scenario,
    letter_world,
    set_opinion,
)


def test_arm_sets_scene_pending_letter_counterpart_and_cooldown() -> None:
    world = letter_world()
    set_opinion(world, -2)

    arm_letter(world, letter_scenario())

    assert world.progress.pending_scene_id == letter_scene_id(world, RIVAL)
    assert world.progress.negotiation_counterpart_id == RIVAL
    assert world.progress.pending_letter == PendingLetter(
        sender_faction_id=RIVAL,
        topic="warning",
        cooldown_until_turn=TURN + DEFAULT_LETTER_COOLDOWN_TURNS,
    )
    assert world.letter_cooldowns[RIVAL] == TURN + DEFAULT_LETTER_COOLDOWN_TURNS


def test_a_scenario_with_letters_off_never_arms() -> None:
    world = letter_world()
    arm_letter(world, letter_scenario(is_enabled=False))
    assert world.progress.pending_scene_id is None
    assert world.progress.pending_letter is None


def test_no_letter_is_armed_while_another_scene_is_pending() -> None:
    world = letter_world()
    pending = UUID(int=9)
    world.progress.pending_scene_id = pending

    arm_letter(world, letter_scenario())

    assert world.progress.pending_scene_id == pending
    assert world.progress.pending_letter is None
    assert world.letter_cooldowns == {}


def test_nothing_arms_without_an_eligible_sender() -> None:
    world = letter_world(is_remembered=False)
    arm_letter(world, letter_scenario())
    assert world.progress.pending_scene_id is None


def test_arming_is_deterministic_for_the_same_world() -> None:
    first, second = letter_world(), letter_world()
    arm_letter(first, letter_scenario())
    arm_letter(second, letter_scenario())
    assert canonical_world_json(first) == canonical_world_json(second)


def test_the_scene_id_depends_on_playthrough_turn_and_sender() -> None:
    world = letter_world()
    other_turn = letter_world(turn=TURN + 1)
    assert letter_scene_id(world, RIVAL) != letter_scene_id(other_turn, RIVAL)
    assert letter_scene_id(world, RIVAL) != letter_scene_id(world, "house_carrow")


def test_empty_letter_state_is_omitted_from_the_world_document() -> None:
    document = letter_world().model_dump(mode="json")
    assert "letter_cooldowns" not in document
    assert "pending_letter" not in document["progress"]


def test_a_document_without_letter_fields_loads_and_round_trips() -> None:
    world = letter_world()
    arm_letter(world, letter_scenario())
    document = world.model_dump(mode="json")
    assert document["progress"]["pending_letter"]["sender_faction_id"] == RIVAL
    restored = WorldState.model_validate(document)
    assert restored.progress.pending_letter == world.progress.pending_letter
    assert restored.letter_cooldowns == world.letter_cooldowns
