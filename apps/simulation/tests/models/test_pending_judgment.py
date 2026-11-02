from app.engine.hashing import canonical_world_json
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_events import PendingJudgment, TurnProgress
from app.models.world_state import WorldState
from strategy_contracts.judgment import JudgmentSubjectKind

from tests.models.builders import make_world


def _pending() -> PendingJudgment:
    return PendingJudgment(
        subject_kind=JudgmentSubjectKind.CAPTIVE,
        subject_id="battle_1:house_ashford:4:1:commander:mira",
        accused_faction_id="house_ashford",
        trigger_event="battle_surrender",
        cooldown_until_turn=10,
    )


def _prisoner() -> PrisonerState:
    return PrisonerState(
        id="p1",
        held_by_id="house_carrow",
        origin_faction_id="house_ashford",
        kind=PrisonerKind.CHARACTER,
        character_id="mira",
    )


def test_pending_judgment_round_trips_through_the_world_document() -> None:
    world = make_world()
    world.progress.pending_judgment = _pending()
    world.judgment_cooldowns["p1"] = 10
    restored = WorldState.model_validate_json(world.model_dump_json())
    assert restored.progress.pending_judgment == _pending()
    assert restored.judgment_cooldowns == {"p1": 10}


def test_a_world_without_judgment_state_serializes_without_the_new_keys() -> None:
    document = canonical_world_json(make_world())
    assert "pending_judgment" not in document
    assert "judgment_cooldowns" not in document
    assert "sentence_ends_turn" not in TurnProgress().model_dump_json()


def test_prisoner_sentence_defaults_to_none_and_is_omitted_when_unset() -> None:
    prisoner = _prisoner()
    assert prisoner.sentence_ends_turn is None
    assert "sentence_ends_turn" not in prisoner.model_dump_json()


def test_prisoner_sentence_round_trips_when_set() -> None:
    prisoner = _prisoner().model_copy(update={"sentence_ends_turn": 9})
    restored = PrisonerState.model_validate_json(prisoner.model_dump_json())
    assert restored.sentence_ends_turn == 9
