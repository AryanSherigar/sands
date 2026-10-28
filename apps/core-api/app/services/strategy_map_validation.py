"""Structural checks on a traced region map, before it is stored."""

from app.integrations import storage_client
from strategy_contracts.map import MapDocument
from strategy_contracts.map_graph import (
    find_disconnected_groups,
    find_duplicate_region_ids,
    find_one_way_links,
)

MAP_IMAGE_KEY_PREFIX = "scenario-maps/"
DISCONNECTED_MESSAGE = "Map is not connected"
FOREIGN_IMAGE_MESSAGE = "Map picture must be uploaded through the map picture upload"


def find_map_problems(document: MapDocument) -> list[str]:
    """Returns one message per problem, in the order the creator should fix them."""
    problems = [
        f"Region id '{region_id}' is used more than once"
        for region_id in find_duplicate_region_ids(document)
    ]
    problems.extend(_find_unknown_references(document))
    problems.extend(
        f"'{region_id}' lists '{neighbor_id}' as a neighbor but not the reverse"
        for region_id, neighbor_id in find_one_way_links(document)
    )
    if find_disconnected_groups(document):
        problems.append(DISCONNECTED_MESSAGE)
    return problems


def _find_unknown_references(document: MapDocument) -> list[str]:
    known_ids = {region.id for region in document.regions}
    referenced = [
        (region.id, neighbor_id)
        for region in document.regions
        for neighbor_id in region.neighbor_ids
    ]
    referenced.extend((road.region_a, road.region_b) for road in document.roads)
    return [
        f"'{source_id}' refers to unknown region '{target_id}'"
        for source_id, target_id in referenced
        if target_id not in known_ids or source_id not in known_ids
    ]


def is_map_image_url_allowed(image_url: str | None) -> bool:
    if image_url is None:
        return True
    object_key = storage_client.object_key_from_url(image_url)
    return object_key is not None and object_key.startswith(MAP_IMAGE_KEY_PREFIX)
