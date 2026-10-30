import pytest
from builders import make_map, make_region
from pydantic import ValidationError
from strategy_contracts.limits import MAX_OUTLINE_CHARS, MAX_REGIONS
from strategy_contracts.map import MapDocument, Point


def test_json_round_trip_keeps_equality() -> None:
    document = make_map({"aa": ["bb"], "bb": ["aa", "cc"], "cc": ["bb"]})
    restored = MapDocument.model_validate_json(document.model_dump_json())
    assert restored == document


def test_oversized_outline_is_rejected() -> None:
    region = make_region("aa", [])
    with pytest.raises(ValidationError):
        region.model_validate(
            {**region.model_dump(), "outline": "M" * (MAX_OUTLINE_CHARS + 1)}
        )


def test_too_many_regions_is_rejected() -> None:
    regions = [make_region(f"region_{index}", []) for index in range(MAX_REGIONS + 1)]
    with pytest.raises(ValidationError):
        MapDocument(width=1, height=1, regions=regions)


def test_unknown_terrain_is_rejected() -> None:
    payload = make_region("aa", []).model_dump(mode="json")
    payload["terrain"] = "lava"
    with pytest.raises(ValidationError):
        make_region("aa", []).model_validate(payload)


def test_float_coordinate_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Point(x=1.5, y=2)
