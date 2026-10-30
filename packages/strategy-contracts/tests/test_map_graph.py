from builders import make_map
from strategy_contracts.map import MapDocument
from strategy_contracts.map_graph import (
    find_disconnected_groups,
    find_duplicate_region_ids,
    find_one_way_links,
)


def test_ring_has_no_problems() -> None:
    ring = make_map(
        {"aa": ["bb", "dd"], "bb": ["aa", "cc"], "cc": ["bb", "dd"], "dd": ["cc", "aa"]}
    )
    assert find_one_way_links(ring) == []
    assert find_disconnected_groups(ring) == []


def test_one_way_link_is_reported() -> None:
    document = make_map({"aa": ["bb"], "bb": []})
    assert find_one_way_links(document) == [("aa", "bb")]


def test_one_way_link_still_counts_for_connectivity() -> None:
    document = make_map({"aa": ["bb"], "bb": []})
    assert find_disconnected_groups(document) == []


def test_two_pairs_are_two_groups_sorted_by_smallest_member() -> None:
    document = make_map({"aa": ["bb"], "bb": ["aa"], "cc": ["dd"], "dd": ["cc"]})
    assert find_disconnected_groups(document) == [
        frozenset({"aa", "bb"}),
        frozenset({"cc", "dd"}),
    ]


def test_duplicate_ids_are_reported_once() -> None:
    document = make_map({"aa": [], "bb": []})
    duplicated = MapDocument(
        width=1,
        height=1,
        regions=[*document.regions, document.regions[0], document.regions[0]],
    )
    assert find_duplicate_region_ids(duplicated) == ["aa"]


def test_empty_map_has_no_problems() -> None:
    empty = MapDocument()
    assert find_one_way_links(empty) == []
    assert find_disconnected_groups(empty) == []
    assert find_duplicate_region_ids(empty) == []


def test_link_to_unknown_region_does_not_crash() -> None:
    document = make_map({"aa": ["nowhere"]})
    assert find_one_way_links(document) == []
    assert find_disconnected_groups(document) == []
