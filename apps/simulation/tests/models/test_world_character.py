import pytest
from app.models.world_character import (
    CommanderState,
    CommanderStatus,
    GovernorState,
    LeaderState,
    MemoryState,
    OpinionReason,
    OpinionState,
)
from pydantic import ValidationError


def _leader() -> LeaderState:
    return LeaderState(
        id="mira",
        name="Mira",
        faction_id="house_ashford",
        trait_ids=["cunning"],
        ambition_ids=["ambition_expand"],
        age=41,
        memories=[MemoryState(kind="betrayal", turn=2, subject_id="harl", weight=3)],
        opinions={
            "harl": OpinionState(
                target_id="harl",
                reasons=[
                    OpinionReason(cause="border_raid", value=-20, fade_per_turn=1)
                ],
            )
        },
    )


def test_leader_round_trips_with_memories_and_opinions() -> None:
    leader = _leader()
    assert LeaderState.model_validate_json(leader.model_dump_json()) == leader


def test_governor_round_trips() -> None:
    governor = GovernorState(id="gov_oswin", name="Oswin", region_id="brennmoor")
    assert GovernorState.model_validate_json(governor.model_dump_json()) == governor


def test_dead_commander_status_parses_and_unknown_is_rejected() -> None:
    fields = {"id": "cmd_a", "name": "A", "faction_id": "house_a"}
    assert (
        CommanderState.model_validate({**fields, "status": "dead"}).status
        is CommanderStatus.DEAD
    )
    with pytest.raises(ValidationError):
        CommanderState.model_validate({**fields, "status": "flying"})


def test_extra_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GovernorState.model_validate(
            {"id": "gov_a", "name": "A", "region_id": "rr", "secret": 1}
        )
