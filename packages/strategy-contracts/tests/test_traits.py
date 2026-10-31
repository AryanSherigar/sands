import pytest
from pydantic import ValidationError
from strategy_contracts.traits import BUILTIN_TRAITS, TraitAxis, TraitDefinition

EXPECTED_TRAIT_IDS = {
    "honorable",
    "treacherous",
    "proud",
    "wrathful",
    "cautious",
    "pragmatic",
    "cunning",
    "paranoid",
    "trusting",
    "naive",
    "stubborn",
    "calculating",
    "cruel",
    "zealot",
}


def _by_id() -> dict[str, TraitDefinition]:
    return {trait.id: trait for trait in BUILTIN_TRAITS}


def test_builtin_ids_are_unique_and_complete() -> None:
    ids = [trait.id for trait in BUILTIN_TRAITS]
    assert len(ids) == len(set(ids))
    assert set(ids) == EXPECTED_TRAIT_IDS


def test_honor_axis_signs() -> None:
    assert _by_id()["honorable"].effects[TraitAxis.HONOR] >= 2
    assert _by_id()["treacherous"].effects[TraitAxis.HONOR] <= -2


def test_trust_axis_signs() -> None:
    assert _by_id()["paranoid"].effects[TraitAxis.TRUST] <= -2
    assert _by_id()["trusting"].effects[TraitAxis.TRUST] >= 2


def test_zealot_has_strong_zeal() -> None:
    assert _by_id()["zealot"].effects[TraitAxis.ZEAL] >= 2


def test_effect_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TraitDefinition(id="bad_trait", name="Bad", effects={TraitAxis.HONOR: 4})


def test_unknown_axis_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TraitDefinition(id="bad_trait", name="Bad", effects={"luck": 1})


def test_every_builtin_trait_describes_how_the_leader_behaves() -> None:
    assert all(trait.description for trait in BUILTIN_TRAITS)
