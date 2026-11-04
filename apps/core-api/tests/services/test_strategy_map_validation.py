"""Unit tests for the strategy map structural checks."""

import json
from pathlib import Path

import pytest
from app.integrations import storage_client
from app.services.strategy_map_validation import (
    DISCONNECTED_MESSAGE,
    find_map_problems,
    is_map_image_url_allowed,
)
from strategy_contracts.map import MapDocument

TRACED_MAP_PATH = (
    Path(__file__).parents[4]
    / "packages"
    / "strategy-contracts"
    / "tests"
    / "traced_map.json"
)


@pytest.fixture
def traced_document() -> MapDocument:
    return MapDocument.model_validate(json.loads(TRACED_MAP_PATH.read_text()))


def test_the_traced_sample_has_no_problems(traced_document: MapDocument):
    assert find_map_problems(traced_document) == []


def test_every_problem_is_reported_not_just_the_first(traced_document: MapDocument):
    traced_document.regions[0].neighbor_ids.append("region_99")
    for region in traced_document.regions[1:]:
        region.neighbor_ids = []

    problems = find_map_problems(traced_document)

    assert any("region_99" in problem for problem in problems)
    assert DISCONNECTED_MESSAGE in problems


def test_no_picture_is_allowed():
    assert is_map_image_url_allowed(None)


def test_a_picture_from_map_storage_is_allowed():
    assert is_map_image_url_allowed(
        storage_client.public_url_for("scenario-maps/abc.png")
    )


@pytest.mark.parametrize(
    "image_url",
    [
        "https://evil.example.com/scenario-maps/abc.png",
        storage_client.public_url_for("scenario-covers/abc.png"),
    ],
)
def test_a_picture_from_elsewhere_is_rejected(image_url: str):
    assert not is_map_image_url_allowed(image_url)
