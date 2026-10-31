import json
from pathlib import Path

from strategy_contracts.map import MapDocument
from strategy_contracts.map_graph import find_disconnected_groups, find_one_way_links

TRACED_MAP_PATH = Path(__file__).parent / "traced_map.json"
EXPECTED_REGION_COUNT = 8


def _load_traced_map() -> MapDocument:
    return MapDocument.model_validate(json.loads(TRACED_MAP_PATH.read_text()))


def test_frontend_traced_map_is_a_valid_map_document() -> None:
    document = _load_traced_map()
    assert len(document.regions) == EXPECTED_REGION_COUNT


def test_frontend_traced_map_neighbors_are_symmetric_and_connected() -> None:
    document = _load_traced_map()
    assert find_one_way_links(document) == []
    assert find_disconnected_groups(document) == []
