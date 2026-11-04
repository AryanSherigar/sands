"""One map of the Imperial Highway: pins, advisory connections and painted art."""

from scripts.seeding.types import MapSeed, PinSeed
from scripts.zegaris.map_assets import has_map_image, map_image_url

MAP_NAME = "The Imperial Highway"
START_SLUG = "owls_respite"

PINS = (
    PinSeed("owls_respite", 0.50, 0.50),
    PinSeed("east_road", 0.66, 0.50),
    PinSeed("swallowing_ground", 0.66, 0.30),
    PinSeed("blind_shallows", 0.80, 0.56),
    PinSeed("sunken_bazaar", 0.80, 0.76),
    PinSeed("gate_of_the_unsworn", 0.88, 0.46),
    PinSeed("flaxen_wards", 0.94, 0.36),
    PinSeed("amber_promenade", 0.94, 0.22),
    PinSeed("golden_crown", 0.94, 0.08),
    PinSeed("west_road", 0.34, 0.50),
    PinSeed("ruinkrag_outer", 0.20, 0.50),
    PinSeed("council_hall", 0.14, 0.34),
    PinSeed("great_pyres", 0.06, 0.34),
    PinSeed("tally_gate", 0.14, 0.66),
    PinSeed("fissure_depths", 0.06, 0.78),
)
CONNECTIONS = (
    ("owls_respite", "east_road"),
    ("east_road", "blind_shallows"),
    ("east_road", "swallowing_ground"),
    ("blind_shallows", "sunken_bazaar"),
    ("blind_shallows", "gate_of_the_unsworn"),
    ("gate_of_the_unsworn", "flaxen_wards"),
    ("flaxen_wards", "amber_promenade"),
    ("amber_promenade", "golden_crown"),
    ("owls_respite", "west_road"),
    ("west_road", "ruinkrag_outer"),
    ("ruinkrag_outer", "council_hall"),
    ("council_hall", "great_pyres"),
    ("ruinkrag_outer", "tally_gate"),
    ("tally_gate", "fissure_depths"),
)


def map_seeds() -> list[MapSeed]:
    image_url = map_image_url() if has_map_image() else None
    return [MapSeed(MAP_NAME, image_url, PINS, CONNECTIONS, START_SLUG)]
