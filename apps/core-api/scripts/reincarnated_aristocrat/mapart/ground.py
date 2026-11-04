"""The layer under the scenery: floor plans for indoor maps, sea for the
province map and grass clearings elsewhere. All of it is derived from the pins,
so it can never drift away from them.
"""

from PIL import ImageDraw
from scripts.reincarnated_aristocrat.mapart.constants import (
    CANVAS_SIZE,
    CLEARING_RADIUS_PX,
    PALETTE,
    ROOM_DOWN_PX,
    ROOM_HALF_WIDTH_PX,
    ROOM_UP_PX,
    ROOM_WALL_WIDTH_PX,
)
from scripts.reincarnated_aristocrat.mapart.decor import (
    ROOM_MAPS,
    SEA_MAP,
    SEA_POLYGON,
)
from scripts.seeding.types import MapSeed, PinSeed


def _pin_pixels(pin: PinSeed) -> tuple[int, int]:
    return int(pin.x * CANVAS_SIZE[0]), int(pin.y * CANVAS_SIZE[1])


def _draw_room(draw: ImageDraw.ImageDraw, pin: PinSeed) -> None:
    pin_x, pin_y = _pin_pixels(pin)
    box = (
        pin_x - ROOM_HALF_WIDTH_PX,
        pin_y - ROOM_UP_PX,
        pin_x + ROOM_HALF_WIDTH_PX,
        pin_y + ROOM_DOWN_PX,
    )
    draw.rectangle(
        box,
        fill=PALETTE["floor"],
        outline=PALETTE["ink"],
        width=ROOM_WALL_WIDTH_PX,
    )


def _draw_clearing(draw: ImageDraw.ImageDraw, pin: PinSeed) -> None:
    pin_x, pin_y = _pin_pixels(pin)
    radius_x, radius_y = CLEARING_RADIUS_PX
    draw.ellipse(
        (pin_x - radius_x, pin_y - radius_y, pin_x + radius_x, pin_y + radius_y),
        fill=PALETTE["grass"],
    )


def _draw_sea(draw: ImageDraw.ImageDraw) -> None:
    points = [
        (int(x * CANVAS_SIZE[0]), int(y * CANVAS_SIZE[1])) for x, y in SEA_POLYGON
    ]
    draw.polygon(
        points,
        fill=PALETTE["water"],
        outline=PALETTE["ink"],
        width=ROOM_WALL_WIDTH_PX // 2,
    )


def draw_ground(draw: ImageDraw.ImageDraw, seed: MapSeed) -> None:
    if seed.name == SEA_MAP:
        _draw_sea(draw)
    is_indoor = seed.name in ROOM_MAPS
    for pin in seed.pins:
        if is_indoor:
            _draw_room(draw, pin)
        else:
            _draw_clearing(draw, pin)
