"""Hand-placed scenery per map. Positions are normalised and kept clear of every
pin's label box (checked by tests/scripts/reincarnated_aristocrat/test_mapart_decor.py).
"""

from dataclasses import dataclass

from scripts.reincarnated_aristocrat.mapart.glyphs import GlyphKind

TREE = GlyphKind.TREE
HOUSE = GlyphKind.HOUSE
FIELD = GlyphKind.FIELD
WATER = GlyphKind.WATER
HILLS = GlyphKind.HILLS
TOWER = GlyphKind.TOWER
TENT = GlyphKind.TENT


@dataclass(frozen=True)
class Decor:
    kind: GlyphKind
    x: float
    y: float
    size: int


PIN_GLYPHS: dict[str, GlyphKind] = {
    "lamberk_region": GlyphKind.MANOR,
    "canare_region": GlyphKind.CASTLE,
    "kumeil_region": GlyphKind.HOUSE,
    "torbekistan_region": GlyphKind.MANOR,
    "semplar_region": GlyphKind.HOUSE,
    "manor_gate": GlyphKind.SIGN,
    "manor_hall": GlyphKind.MANOR,
    "ars_room": GlyphKind.HOUSE,
    "raven_chamber": GlyphKind.HOUSE,
    "manor_study": GlyphKind.HOUSE,
    "manor_kitchen": GlyphKind.HOUSE,
    "town_square": GlyphKind.SIGN,
    "slave_quarter": GlyphKind.TENT,
    "town_inn": GlyphKind.HOUSE,
    "smithy": GlyphKind.HOUSE,
    "shadow_tavern": GlyphKind.HOUSE,
    "shadow_backroom": GlyphKind.HOUSE,
    "sparring_yard": GlyphKind.SIGN,
    "archery_range": GlyphKind.TOWER,
    "barracks": GlyphKind.TENT,
    "farm_village": GlyphKind.HOUSE,
    "wheat_fields": GlyphKind.FIELD,
    "mill": GlyphKind.MILL,
    "canare_gate": GlyphKind.SIGN,
    "canare_hall": GlyphKind.CASTLE,
    "canare_council": GlyphKind.TOWER,
    "plaid_house": GlyphKind.MANOR,
    "plaid_garden": GlyphKind.TREE,
}

DECOR: dict[str, tuple[Decor, ...]] = {
    "Missian Province": (
        Decor(HILLS, 0.12, 0.18, 40),
        Decor(HILLS, 0.80, 0.20, 40),
        Decor(HILLS, 0.58, 0.10, 34),
        Decor(TREE, 0.07, 0.50, 36),
        Decor(TREE, 0.22, 0.80, 36),
        Decor(TREE, 0.17, 0.34, 34),
        Decor(TREE, 0.88, 0.45, 36),
        Decor(FIELD, 0.60, 0.36, 50),
        Decor(FIELD, 0.62, 0.62, 50),
        Decor(TREE, 0.30, 0.12, 34),
        Decor(TREE, 0.28, 0.90, 34),
        Decor(TREE, 0.80, 0.50, 34),
    ),
    "Louvent Manor": (
        Decor(TREE, 0.07, 0.50, 36),
        Decor(TREE, 0.07, 0.72, 36),
        Decor(TREE, 0.93, 0.15, 36),
        Decor(TREE, 0.15, 0.82, 36),
        Decor(TREE, 0.25, 0.88, 36),
        Decor(FIELD, 0.90, 0.85, 60),
        Decor(HOUSE, 0.30, 0.60, 30),
    ),
    "Lamberk Town": (
        Decor(HOUSE, 0.10, 0.20, 30),
        Decor(HOUSE, 0.25, 0.15, 30),
        Decor(HOUSE, 0.35, 0.30, 30),
        Decor(HOUSE, 0.62, 0.12, 30),
        Decor(HOUSE, 0.90, 0.50, 30),
        Decor(HOUSE, 0.65, 0.85, 30),
        Decor(WATER, 0.45, 0.88, 60),
        Decor(TREE, 0.05, 0.50, 36),
    ),
    "The Shadows' Haunt": (
        Decor(HOUSE, 0.10, 0.20, 30),
        Decor(HOUSE, 0.90, 0.20, 30),
        Decor(HOUSE, 0.50, 0.12, 30),
        Decor(HOUSE, 0.50, 0.85, 30),
        Decor(HOUSE, 0.10, 0.80, 30),
        Decor(HOUSE, 0.90, 0.80, 30),
    ),
    "Training Grounds": (
        Decor(TENT, 0.10, 0.70, 34),
        Decor(TENT, 0.20, 0.85, 34),
        Decor(TENT, 0.90, 0.70, 34),
        Decor(TOWER, 0.90, 0.12, 40),
        Decor(TREE, 0.50, 0.15, 36),
        Decor(FIELD, 0.50, 0.90, 60),
    ),
    "Farmland and Villages": (
        Decor(FIELD, 0.12, 0.75, 60),
        Decor(FIELD, 0.30, 0.88, 60),
        Decor(FIELD, 0.65, 0.88, 60),
        Decor(FIELD, 0.88, 0.70, 60),
        Decor(TREE, 0.50, 0.12, 36),
        Decor(TREE, 0.93, 0.50, 36),
    ),
    "Canare Castle": (
        Decor(TOWER, 0.12, 0.20, 40),
        Decor(TOWER, 0.88, 0.20, 40),
        Decor(TOWER, 0.12, 0.80, 40),
        Decor(TOWER, 0.88, 0.80, 40),
        Decor(TREE, 0.30, 0.50, 36),
        Decor(TREE, 0.70, 0.50, 36),
    ),
    "Plaid Estate": (
        Decor(TREE, 0.90, 0.70, 36),
        Decor(TREE, 0.65, 0.80, 36),
        Decor(TREE, 0.10, 0.30, 36),
        Decor(TREE, 0.45, 0.15, 36),
        Decor(FIELD, 0.15, 0.75, 60),
    ),
}

ROOM_MAPS = frozenset(
    {"Louvent Manor", "Canare Castle", "The Shadows' Haunt", "Plaid Estate"}
)

SEA_POLYGON = (
    (0.66, 1.0),
    (0.74, 0.94),
    (0.84, 0.84),
    (0.93, 0.72),
    (1.0, 0.66),
    (1.0, 1.0),
)
SEA_MAP = "Missian Province"
