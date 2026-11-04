"""The Floor 9 map: nine location pins and the walkable connections (no image)."""

from scripts.seeding.types import PinSeed

MAP_NAME = "Floor 9"
START_SLUG = "night_desk"


PINS: tuple[PinSeed, ...] = (
    PinSeed("elevator_lobby", 0.10, 0.50),
    PinSeed("night_desk", 0.28, 0.50),
    PinSeed("east_corridor", 0.55, 0.30),
    PinSeed("east_alcove", 0.50, 0.10),
    PinSeed("records_room", 0.62, 0.52),
    PinSeed("cabin_approach", 0.82, 0.30),
    PinSeed("cabin_14", 0.95, 0.30),
    PinSeed("print_room", 0.20, 0.82),
    PinSeed("stairwell_door", 0.06, 0.82),
)

CONNECTIONS: tuple[tuple[str, str], ...] = (
    ("elevator_lobby", "night_desk"),
    ("night_desk", "east_corridor"),
    ("east_corridor", "east_alcove"),
    ("east_corridor", "records_room"),
    ("east_corridor", "cabin_approach"),
    ("cabin_approach", "cabin_14"),
    ("night_desk", "print_room"),
    ("night_desk", "stairwell_door"),
)
