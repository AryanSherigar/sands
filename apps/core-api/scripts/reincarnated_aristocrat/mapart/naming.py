import re

from scripts.seeding.types import MapSeed

SLUG_SEPARATOR_PATTERN = re.compile(r"[^a-z0-9]+")


def map_file_name(seed: MapSeed) -> str:
    slug = SLUG_SEPARATOR_PATTERN.sub("-", seed.name.lower()).strip("-")
    return f"{slug}.png"
