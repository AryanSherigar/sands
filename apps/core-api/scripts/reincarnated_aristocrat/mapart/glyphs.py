from collections.abc import Callable
from enum import StrEnum

from PIL import ImageDraw
from scripts.reincarnated_aristocrat.mapart.constants import OUTLINE_WIDTH_PX, PALETTE

Box = tuple[int, int, int, int]
Center = tuple[int, int]


class GlyphKind(StrEnum):
    HOUSE = "house"
    MANOR = "manor"
    CASTLE = "castle"
    TOWER = "tower"
    TENT = "tent"
    TREE = "tree"
    FIELD = "field"
    MILL = "mill"
    WATER = "water"
    HILLS = "hills"
    SIGN = "sign"


def _outlined_polygon(
    draw: ImageDraw.ImageDraw, points: list[Center], fill_name: str
) -> None:
    draw.polygon(
        points,
        fill=PALETTE[fill_name],
        outline=PALETTE["ink"],
        width=OUTLINE_WIDTH_PX,
    )


def _outlined_rectangle(draw: ImageDraw.ImageDraw, box: Box, fill_name: str) -> None:
    draw.rectangle(
        box, fill=PALETTE[fill_name], outline=PALETTE["ink"], width=OUTLINE_WIDTH_PX
    )


def _draw_house(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 2
    _outlined_rectangle(draw, (cx - half, cy - half // 2, cx + half, cy + half), "wood")
    _outlined_polygon(
        draw,
        [
            (cx - half - 4, cy - half // 2),
            (cx, cy - size),
            (cx + half + 4, cy - half // 2),
        ],
        "roof",
    )
    return (cx - half - 4, cy - size, cx + half + 4, cy + half)


def _draw_manor(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    wing = size
    _outlined_rectangle(
        draw, (cx - wing, cy - size // 3, cx + wing, cy + size // 2), "stone"
    )
    _outlined_polygon(
        draw,
        [
            (cx - wing - 4, cy - size // 3),
            (cx, cy - size),
            (cx + wing + 4, cy - size // 3),
        ],
        "roof",
    )
    _outlined_rectangle(draw, (cx - 6, cy, cx + 6, cy + size // 2), "wood")
    return (cx - wing - 4, cy - size, cx + wing + 4, cy + size // 2)


def _draw_tower(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 3
    _outlined_rectangle(
        draw, (cx - half, cy - size, cx + half, cy + size // 2), "stone"
    )
    for offset in (-half, 0, half - half // 2):
        left = cx + offset
        _outlined_rectangle(
            draw, (left, cy - size - 10, left + half // 2, cy - size), "stone"
        )
    return (cx - half, cy - size - 10, cx + half, cy + size // 2)


def _draw_castle(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    _outlined_rectangle(
        draw, (cx - size, cy - size // 2, cx + size, cy + size // 2), "stone"
    )
    for side in (-size, size - size // 3):
        _draw_tower(draw, (cx + side + size // 6, cy - size // 6), size // 2)
    _outlined_rectangle(draw, (cx - 8, cy, cx + 8, cy + size // 2), "wood")
    return (cx - size, cy - size, cx + size, cy + size // 2)


def _draw_tent(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 2
    _outlined_polygon(
        draw,
        [(cx - half - 6, cy + half), (cx, cy - size), (cx + half + 6, cy + half)],
        "roof",
    )
    _outlined_polygon(
        draw, [(cx - 8, cy + half), (cx, cy - 4), (cx + 8, cy + half)], "ink_faint"
    )
    return (cx - half - 6, cy - size, cx + half + 6, cy + half)


def _draw_tree(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 2
    _outlined_rectangle(draw, (cx - 4, cy, cx + 4, cy + half), "wood")
    draw.ellipse(
        (cx - half, cy - size, cx + half, cy + half // 2),
        fill=PALETTE["forest"],
        outline=PALETTE["ink"],
        width=OUTLINE_WIDTH_PX,
    )
    return (cx - half, cy - size, cx + half, cy + half)


def _draw_field(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    box = (cx - size, cy - size // 2, cx + size, cy + size // 2)
    _outlined_rectangle(draw, box, "field")
    for row in range(box[1] + 10, box[3], 14):
        draw.line(
            (box[0] + 4, row, box[2] - 4, row), fill=PALETTE["ink_faint"], width=2
        )
    return box


def _draw_mill(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 2
    _outlined_polygon(
        draw,
        [
            (cx - half, cy + half),
            (cx - half // 2, cy - half),
            (cx + half // 2, cy - half),
            (cx + half, cy + half),
        ],
        "stone",
    )
    top = (cx, cy - half)
    for dx, dy in (
        (-size, -size),
        (size, -size),
        (-size, size // 2),
        (size, size // 2),
    ):
        draw.line(
            (*top, cx + dx, cy - half + dy), fill=PALETTE["ink"], width=OUTLINE_WIDTH_PX
        )
    return (cx - size, cy - half - size, cx + size, cy + half)


def _draw_water(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    box = (cx - size, cy - size // 2, cx + size, cy + size // 2)
    draw.ellipse(
        box, fill=PALETTE["water"], outline=PALETTE["ink"], width=OUTLINE_WIDTH_PX
    )
    for offset in (-size // 3, 0, size // 3):
        wave = (cx + offset - 14, cy - 8, cx + offset + 14, cy + 8)
        draw.arc(wave, 200, 340, fill=PALETTE["paper"], width=3)
    return box


def _draw_hills(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    for offset in (-size, 0, size):
        peak = (cx + offset, cy - size // 2)
        _outlined_polygon(
            draw,
            [
                (peak[0] - size // 2 - 6, cy + size // 3),
                peak,
                (peak[0] + size // 2 + 6, cy + size // 3),
            ],
            "stone",
        )
    return (
        cx - size - size // 2 - 6,
        cy - size // 2,
        cx + size + size // 2 + 6,
        cy + size // 3,
    )


def _draw_sign(draw: ImageDraw.ImageDraw, center: Center, size: int) -> Box:
    cx, cy = center
    half = size // 2
    _outlined_rectangle(draw, (cx - 4, cy - half, cx + 4, cy + half), "wood")
    _outlined_rectangle(draw, (cx - half, cy - half, cx + half, cy - half // 4), "wood")
    return (cx - half, cy - half, cx + half, cy + half)


_DRAWERS: dict[GlyphKind, Callable[[ImageDraw.ImageDraw, Center, int], Box]] = {
    GlyphKind.HOUSE: _draw_house,
    GlyphKind.MANOR: _draw_manor,
    GlyphKind.CASTLE: _draw_castle,
    GlyphKind.TOWER: _draw_tower,
    GlyphKind.TENT: _draw_tent,
    GlyphKind.TREE: _draw_tree,
    GlyphKind.FIELD: _draw_field,
    GlyphKind.MILL: _draw_mill,
    GlyphKind.WATER: _draw_water,
    GlyphKind.HILLS: _draw_hills,
    GlyphKind.SIGN: _draw_sign,
}


def draw_glyph(
    draw: ImageDraw.ImageDraw, kind: GlyphKind, center: Center, size: int
) -> Box:
    return _DRAWERS[kind](draw, center, size)
