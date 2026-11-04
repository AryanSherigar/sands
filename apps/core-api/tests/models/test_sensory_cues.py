import pytest
from app.models.condition import (
    SENSORY_CUE_IDS,
    ConditionCreate,
    ConditionResponse,
    ConditionUpdate,
)
from pydantic import ValidationError


def _create(**overrides) -> ConditionCreate:
    return ConditionCreate(label="Phone", narrator_instruction="It rings.", **overrides)


def test_cue_ids_are_the_ten_designed_cues_in_order() -> None:
    assert SENSORY_CUE_IDS == (
        "phone_ring",
        "heavy_knock",
        "light_buzz",
        "distant_footsteps",
        "sudden_silence",
        "radio_static",
        "elevator_chime",
        "lamp_click",
        "keyboard_typing",
        "paper_rustle",
    )


def test_cue_fields_default_to_no_cue_cut_ambient_and_800ms() -> None:
    condition = _create()

    assert condition.sensory_cue is None
    assert condition.cut_ambient is True
    assert condition.silence_duration_ms == 800


@pytest.mark.parametrize("cue", SENSORY_CUE_IDS)
def test_every_known_cue_is_accepted(cue: str) -> None:
    assert _create(sensory_cue=cue).sensory_cue == cue


def test_unknown_cue_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(sensory_cue="air_horn")


@pytest.mark.parametrize("silence_ms", [-1, 5001])
def test_silence_duration_outside_0_to_5000_is_rejected(silence_ms: int) -> None:
    with pytest.raises(ValidationError):
        _create(silence_duration_ms=silence_ms)


@pytest.mark.parametrize("silence_ms", [0, 5000])
def test_silence_duration_bounds_are_inclusive(silence_ms: int) -> None:
    assert _create(silence_duration_ms=silence_ms).silence_duration_ms == silence_ms


def test_update_leaves_unset_cue_fields_unset() -> None:
    update = ConditionUpdate(label="Renamed")

    assert update.model_fields_set == {"label"}


def test_update_validates_cue_id() -> None:
    with pytest.raises(ValidationError):
        ConditionUpdate(sensory_cue="air_horn")


def test_response_exposes_cue_fields() -> None:
    response = ConditionResponse.model_validate(
        {
            "condition_id": "5b0bfb60-5a9e-4d7b-9d75-7a4f0e8e7e11",
            "scenario_id": "5b0bfb60-5a9e-4d7b-9d75-7a4f0e8e7e12",
            "label": "Phone",
            "narrator_instruction": "It rings.",
            "sensory_cue": "phone_ring",
            "cut_ambient": False,
            "silence_duration_ms": 1200,
        }
    )

    assert (response.sensory_cue, response.cut_ambient) == ("phone_ring", False)
    assert response.silence_duration_ms == 1200
