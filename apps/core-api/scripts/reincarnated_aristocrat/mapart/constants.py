from pathlib import Path

CANVAS_SIZE = (1600, 900)
LABEL_BOX = (240, 44)
GLYPH_LIFT_PX = 54
PIN_GLYPH_SIZE = 40
BORDER_WIDTH_PX = 6
BORDER_INSET_PX = 14

TONE_GRID = (50, 28)
TONE_ALPHA = 0.18
VIGNETTE_ALPHA = 0.55
OUTLINE_WIDTH_PX = 3

MAP_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "maps"

PALETTE: dict[str, tuple[int, int, int]] = {
    "paper": (226, 207, 166),
    "paper_edge": (150, 112, 70),
    "ink": (62, 42, 28),
    "ink_faint": (120, 94, 66),
    "water": (120, 150, 160),
    "field": (190, 176, 104),
    "forest": (96, 120, 78),
    "stone": (150, 142, 130),
    "wood": (140, 96, 60),
    "roof": (160, 70, 50),
    "floor": (203, 183, 140),
    "grass": (186, 188, 128),
}

ROOM_WALL_WIDTH_PX = 6
ROOM_HALF_WIDTH_PX = 170
ROOM_UP_PX = 120
ROOM_DOWN_PX = 56
CLEARING_RADIUS_PX = (230, 120)
