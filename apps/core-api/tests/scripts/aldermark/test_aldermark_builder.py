import uuid

import pytest
from scripts.aldermark.builder import (
    CONTENT_TAG,
    AldermarkNotPublishableError,
    ensure_publishable,
    load_strategy_document,
    scenario_columns,
)
from scripts.aldermark.ids import NAMESPACE, SCENARIO_ID
from scripts.aldermark.map_assets import MAP_ASSET_PATH, has_map_image

MAP_URL = "https://media.example.test/aldermark/map.webp"


def test_the_painted_map_ships_with_the_scripts() -> None:
    assert has_map_image()
    assert MAP_ASSET_PATH.stat().st_size > 0


def test_the_document_map_points_at_the_stored_image() -> None:
    document = load_strategy_document(MAP_URL)

    assert document["map"]["image_url"] == MAP_URL


def test_the_traced_document_passes_the_publish_checks() -> None:
    ensure_publishable(load_strategy_document(MAP_URL))


def test_a_document_the_publish_checks_refuse_is_rejected_before_any_write() -> None:
    document = load_strategy_document(MAP_URL)
    document["factions"] = []

    with pytest.raises(AldermarkNotPublishableError):
        ensure_publishable(document)


def test_columns_describe_a_public_strategy_scenario() -> None:
    columns = scenario_columns(MAP_URL)

    assert columns["mode"] == "strategy"
    assert columns["complexity_tier"] == "master"
    assert columns["visibility"] == "public"
    assert columns["content_tag"] == CONTENT_TAG
    assert columns["cover_image_url"] == MAP_URL
    assert columns["strategy_document"]["map"]["image_url"] == MAP_URL


def test_the_scenario_id_derives_from_the_namespace_so_reseeding_is_idempotent() -> (
    None
):
    assert uuid.uuid5(NAMESPACE, "scenario:aldermark") == SCENARIO_ID
