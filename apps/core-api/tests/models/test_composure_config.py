import pytest
from app.models.minigame import (
    COMPOSURE_TYPE,
    ComposureConfig,
    DodgeConfig,
    LockpickConfig,
    MinigameCreate,
    MinigameResponse,
    MinigameUpdate,
)
from pydantic import ValidationError


def _create(**overrides) -> MinigameCreate:
    base = {
        "label": "The stairwell hum",
        "minigame_type": COMPOSURE_TYPE,
        "outcome_mode": "binary",
        "win_mutations": [{"path": "sanity", "op": "increment", "value": 5}],
        "lose_mutations": [{"path": "sanity", "op": "decrement", "value": 20}],
        "composure_config": ComposureConfig(),
    }
    base.update(overrides)
    return MinigameCreate(**base)


def test_defaults_match_the_spec() -> None:
    config = ComposureConfig()

    assert config.target_bpm == 55
    assert config.beats_to_win == 5
    assert config.tolerance_ms == 180
    assert config.max_strikes == 2
    assert config.keys == ["W", "A", "S", "D"]
    assert config.audio_profile == "hum"
    assert config.version == 1
    assert config.texts.start_text == "Begin"


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_bpm": 29},
        {"target_bpm": 121},
        {"beats_to_win": 2},
        {"beats_to_win": 13},
        {"tolerance_ms": 79},
        {"tolerance_ms": 401},
        {"max_strikes": 0},
        {"max_strikes": 6},
        {"keys": []},
        {"keys": ["Q"]},
        {"keys": ["W", "W"]},
        {"audio_profile": "shout"},
        {"version": 2},
    ],
)
def test_out_of_range_config_is_rejected(overrides) -> None:
    with pytest.raises(ValidationError):
        ComposureConfig(**overrides)


def test_bounds_are_inclusive() -> None:
    ComposureConfig(target_bpm=30, beats_to_win=3, tolerance_ms=80, max_strikes=1)
    ComposureConfig(target_bpm=120, beats_to_win=12, tolerance_ms=400, max_strikes=5)


def test_unknown_stored_fields_are_ignored() -> None:
    config = ComposureConfig.model_validate({"target_bpm": 60, "legacy_field": 1})

    assert config.target_bpm == 60


def test_texts_are_bounded() -> None:
    with pytest.raises(ValidationError):
        ComposureConfig(texts={"instructions": "x" * 1001})
    with pytest.raises(ValidationError):
        ComposureConfig(texts={"win_text": ""})


def test_composure_type_requires_its_config() -> None:
    with pytest.raises(ValidationError):
        _create(composure_config=None)


def test_composure_type_rejects_other_types_configs() -> None:
    with pytest.raises(ValidationError):
        _create(dodge_config=DodgeConfig(difficulty=3))
    with pytest.raises(ValidationError):
        _create(lockpick_config=LockpickConfig(difficulty=3, picks=3))


@pytest.mark.parametrize("minigame_type", ["dodge", "lockpick"])
def test_composure_config_is_rejected_on_other_types(minigame_type: str) -> None:
    other_config = (
        {"dodge_config": DodgeConfig(difficulty=3)}
        if minigame_type == "dodge"
        else {"lockpick_config": LockpickConfig(difficulty=3, picks=3)}
    )

    with pytest.raises(ValidationError):
        _create(minigame_type=minigame_type, **other_config)


def test_a_valid_composure_minigame_is_accepted() -> None:
    created = _create(composure_config=ComposureConfig(target_bpm=70, keys=["W"]))

    assert created.composure_config.target_bpm == 70
    assert created.composure_config.keys == ["W"]


def test_update_accepts_a_composure_config() -> None:
    update = MinigameUpdate(composure_config=ComposureConfig(max_strikes=3))

    assert update.model_dump(exclude_unset=True)["composure_config"]["max_strikes"] == 3


def test_response_round_trips_the_config_from_a_stored_dict() -> None:
    response = MinigameResponse(
        minigame_id="00000000-0000-0000-0000-000000000001",
        scenario_id="00000000-0000-0000-0000-000000000002",
        label="hum",
        minigame_type=COMPOSURE_TYPE,
        outcome_mode="binary",
        composure_config={"target_bpm": 44},
    )

    assert response.composure_config.target_bpm == 44
    assert response.composure_config.beats_to_win == 5
