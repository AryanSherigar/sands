"""Map layouts. One layout drives both the drawing and the pins, so the art and
the pins can never drift apart. Positions are normalised (0 to 1) and are this
scenario's own arrangement; the regional layout loosely follows the canon
geography (Lamberk inside Canare, Kumeil and Torbekistan to the south-west and
south, Semplar on the southern coast).
"""

from dataclasses import replace

from scripts.reincarnated_aristocrat.map_assets import map_image_url
from scripts.reincarnated_aristocrat.mapart.naming import map_file_name
from scripts.seeding.types import MapSeed, PinSeed

START_SLUG = "ars_room"
REGIONAL_NAME = "Missian Province"

REGIONAL_PINS = (
    PinSeed("lamberk_region", 0.30, 0.30),
    PinSeed("canare_region", 0.44, 0.46),
    PinSeed("kumeil_region", 0.18, 0.62),
    PinSeed("torbekistan_region", 0.40, 0.76),
    PinSeed("semplar_region", 0.64, 0.90),
)
REGIONAL_CONNECTIONS = (
    ("lamberk_region", "canare_region"),
    ("lamberk_region", "kumeil_region"),
    ("canare_region", "torbekistan_region"),
    ("kumeil_region", "torbekistan_region"),
    ("torbekistan_region", "semplar_region"),
)
ENTRANCE_CONNECTIONS = (
    ("lamberk_region", "manor_gate"),
    ("lamberk_region", "town_square"),
    ("lamberk_region", "sparring_yard"),
    ("lamberk_region", "farm_village"),
    ("canare_region", "canare_gate"),
    ("torbekistan_region", "plaid_house"),
    ("town_square", "shadow_tavern"),
)

INTERIORS: tuple[tuple[str, tuple[PinSeed, ...], tuple[tuple[str, str], ...]], ...] = (
    (
        "Louvent Manor",
        (
            PinSeed("manor_gate", 0.50, 0.90),
            PinSeed("manor_hall", 0.50, 0.62),
            PinSeed("ars_room", 0.22, 0.26),
            PinSeed("raven_chamber", 0.50, 0.20),
            PinSeed("manor_study", 0.78, 0.30),
            PinSeed("manor_kitchen", 0.80, 0.66),
        ),
        (
            ("manor_gate", "manor_hall"),
            ("manor_hall", "ars_room"),
            ("manor_hall", "raven_chamber"),
            ("manor_hall", "manor_study"),
            ("manor_hall", "manor_kitchen"),
        ),
    ),
    (
        "Lamberk Town",
        (
            PinSeed("town_square", 0.50, 0.50),
            PinSeed("slave_quarter", 0.22, 0.78),
            PinSeed("town_inn", 0.78, 0.28),
            PinSeed("smithy", 0.80, 0.72),
        ),
        (
            ("town_square", "slave_quarter"),
            ("town_square", "town_inn"),
            ("town_square", "smithy"),
        ),
    ),
    (
        "The Shadows' Haunt",
        (
            PinSeed("shadow_tavern", 0.32, 0.50),
            PinSeed("shadow_backroom", 0.70, 0.50),
        ),
        (("shadow_tavern", "shadow_backroom"),),
    ),
    (
        "Training Grounds",
        (
            PinSeed("sparring_yard", 0.50, 0.58),
            PinSeed("archery_range", 0.80, 0.28),
            PinSeed("barracks", 0.22, 0.28),
        ),
        (("sparring_yard", "archery_range"), ("sparring_yard", "barracks")),
    ),
    (
        "Farmland and Villages",
        (
            PinSeed("farm_village", 0.50, 0.62),
            PinSeed("wheat_fields", 0.22, 0.30),
            PinSeed("mill", 0.80, 0.30),
        ),
        (("farm_village", "wheat_fields"), ("farm_village", "mill")),
    ),
    (
        "Canare Castle",
        (
            PinSeed("canare_gate", 0.50, 0.88),
            PinSeed("canare_hall", 0.50, 0.55),
            PinSeed("canare_council", 0.50, 0.20),
        ),
        (("canare_gate", "canare_hall"), ("canare_hall", "canare_council")),
    ),
    (
        "Plaid Estate",
        (
            PinSeed("plaid_house", 0.46, 0.58),
            PinSeed("plaid_garden", 0.76, 0.30),
        ),
        (("plaid_house", "plaid_garden"),),
    ),
)


def _with_image(layout: MapSeed) -> MapSeed:
    return replace(layout, image_url=map_image_url(map_file_name(layout)))


def regional_map(with_images: bool = True) -> MapSeed:
    layout = MapSeed(
        name=REGIONAL_NAME,
        image_url=None,
        pins=REGIONAL_PINS,
        connections=(*REGIONAL_CONNECTIONS, *ENTRANCE_CONNECTIONS),
        display_order=0,
    )
    return _with_image(layout) if with_images else layout


def interior_maps(with_images: bool = True) -> list[MapSeed]:
    layouts = [
        MapSeed(
            name=name,
            image_url=None,
            pins=pins,
            connections=connections,
            start_slug=START_SLUG if name == "Louvent Manor" else None,
            display_order=index,
        )
        for index, (name, pins, connections) in enumerate(INTERIORS, start=1)
    ]
    return [_with_image(layout) for layout in layouts] if with_images else layouts


def map_seeds(with_images: bool = True) -> list[MapSeed]:
    return [regional_map(with_images), *interior_maps(with_images)]
