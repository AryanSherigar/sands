from uuid import UUID

import pytest
from app.engine.hashing import world_hash
from app.engine.letters.arming import arm_letter
from app.engine.letters.closing import close_letter
from app.engine.letters.constants import (
    ACK_WARNING_WEIGHT,
    LETTER_ACK_WARNING,
    LETTER_COOLER,
    LETTER_NO_EFFECT,
    LETTER_WARMER,
    WARNING_ACKNOWLEDGED,
)
from app.engine.opinion import opinion_of
from app.exceptions.command_exceptions import CampaignProgressError
from strategy_contracts.scene import ChoiceOutcome, ProseOnlyOutcome

from tests.engine.letters.builders import (
    PLAYER_LEADER,
    RIVAL_LEADER,
    letter_scenario,
    letter_world,
    set_opinion,
)


def _armed():
    world = letter_world()
    set_opinion(world, 2)
    scenario = letter_scenario()
    arm_letter(world, scenario)
    return world, scenario, world.progress.pending_scene_id


def _close(option_id: str):
    world, scenario, scene_id = _armed()
    closed, events = close_letter(
        world, scenario, scene_id, ChoiceOutcome(option_id=option_id)
    )
    return world, closed, events


def _opinion(world) -> int:
    return opinion_of(world.leaders[RIVAL_LEADER], PLAYER_LEADER)


def test_warmer_adds_a_fading_plus_five_opinion_reason() -> None:
    before, after, _ = _close(LETTER_WARMER)
    assert _opinion(after) == _opinion(before) + 5
    reason = after.leaders[RIVAL_LEADER].opinions[PLAYER_LEADER].reasons[-1]
    assert (reason.cause, reason.value, reason.fade_per_turn) == ("letter_warm", 5, 1)


def test_cooler_adds_a_minus_five_opinion_reason() -> None:
    before, after, _ = _close(LETTER_COOLER)
    assert _opinion(after) == _opinion(before) - 5


def test_acknowledging_a_warning_records_a_memory_and_leaves_opinion_alone() -> None:
    before, after, _ = _close(LETTER_ACK_WARNING)
    assert _opinion(after) == _opinion(before)
    recorded = next(
        item
        for item in after.leaders[RIVAL_LEADER].memories
        if item.kind == WARNING_ACKNOWLEDGED
    )
    assert (recorded.weight, recorded.subject_id) == (ACK_WARNING_WEIGHT, PLAYER_LEADER)


def test_no_effect_changes_nothing_but_the_pending_scene() -> None:
    before, after, _ = _close(LETTER_NO_EFFECT)
    assert _opinion(after) == _opinion(before)
    assert after.leaders[RIVAL_LEADER].memories == before.leaders[RIVAL_LEADER].memories


@pytest.mark.parametrize(
    "option_id", [LETTER_WARMER, LETTER_COOLER, LETTER_ACK_WARNING, LETTER_NO_EFFECT]
)
def test_every_option_clears_the_pending_letter_state(option_id: str) -> None:
    _, after, _ = _close(option_id)
    assert after.progress.pending_scene_id is None
    assert after.progress.pending_letter is None
    assert after.progress.negotiation_counterpart_id is None


def test_the_sender_cooldown_set_at_arming_survives_closing() -> None:
    before, after, _ = _close(LETTER_NO_EFFECT)
    assert after.letter_cooldowns == before.letter_cooldowns != {}


def test_closing_does_not_mutate_the_input_world() -> None:
    world, scenario, scene_id = _armed()
    fingerprint = world_hash(world)
    close_letter(world, scenario, scene_id, ChoiceOutcome(option_id=LETTER_WARMER))
    assert world_hash(world) == fingerprint


def test_closing_is_deterministic_for_replay() -> None:
    first = _close(LETTER_WARMER)[1]
    second = _close(LETTER_WARMER)[1]
    assert world_hash(first) == world_hash(second)


def test_a_different_scene_id_is_refused() -> None:
    world, scenario, _ = _armed()
    with pytest.raises(CampaignProgressError):
        close_letter(
            world, scenario, UUID(int=5), ChoiceOutcome(option_id=LETTER_NO_EFFECT)
        )


def test_an_unknown_option_is_refused() -> None:
    world, scenario, scene_id = _armed()
    with pytest.raises(CampaignProgressError):
        close_letter(world, scenario, scene_id, ChoiceOutcome(option_id="gift_gold"))


def test_a_non_choice_outcome_is_refused() -> None:
    world, scenario, scene_id = _armed()
    with pytest.raises(CampaignProgressError):
        close_letter(world, scenario, scene_id, ProseOnlyOutcome())
