import pytest
from app.models.world_player import PlayerProfile, PlayerRuler
from pydantic import ValidationError


def _ruler(**overrides: object) -> PlayerRuler:
    fields: dict[str, object] = {
        "name": "Valdren",
        "trait_ids": ["honorable", "cautious"],
        "ambition_ids": ["ambition_peace"],
    }
    fields.update(overrides)
    return PlayerRuler.model_validate(fields)


@pytest.mark.parametrize("trait_ids", [["honorable"], ["a_a", "b_b", "c_c", "d_d"]])
def test_ruler_trait_count_is_bounded(trait_ids: list[str]) -> None:
    with pytest.raises(ValidationError):
        _ruler(trait_ids=trait_ids)


def test_ruler_ambition_count_is_bounded() -> None:
    with pytest.raises(ValidationError):
        _ruler(ambition_ids=[])
    with pytest.raises(ValidationError):
        _ruler(ambition_ids=["a_a", "b_b", "c_c"])


def test_ruler_and_profile_round_trip() -> None:
    ruler = _ruler()
    profile = PlayerProfile(tactic_use_counts={"ambush": 2}, promises_kept=1)
    assert PlayerRuler.model_validate_json(ruler.model_dump_json()) == ruler
    assert PlayerProfile.model_validate_json(profile.model_dump_json()) == profile


def test_negative_counter_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PlayerProfile(wars_declared=-1)
