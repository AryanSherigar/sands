"""Flat-color guide image for the Imperial Highway, repainted by strategy's art step.

Same two-step shape as strategy map generation: flat regions first, then the
watercolor repaint. The regions are drawn from the seeded pin positions so the
painted terrain agrees with where the pins sit.
"""

import itertools
import random
from io import BytesIO

from PIL import Image, ImageDraw

GUIDE_SIZE = (1792, 1344)
JITTER_SEED = 41
EDGE_JITTER_PX = 14
EDGE_STEPS = 24
ROAD_HALF_WIDTH_PX = 9

CRAGS = (150, 60, 60)
PASS = (230, 190, 60)
VALLEY = (70, 170, 90)
SHALLOWS = (150, 110, 60)
TIER_COLORS = ((235, 235, 250), (250, 225, 235), (225, 250, 250))
CHASM = (30, 30, 90)
ROAD = (250, 250, 250)

Point = tuple[float, float]

CRAG_EDGE: tuple[Point, ...] = ((0.38, 0.0), (0.34, 0.5), (0.40, 1.0))
VALLEY_EDGE: tuple[Point, ...] = ((0.62, 0.0), (0.66, 0.5), (0.60, 1.0))
TERRACE_LEFT = 0.87
TIER_BREAKS = (0.0, 0.15, 0.29, 0.45)
SHALLOWS_CENTER = (0.80, 0.68)
SHALLOWS_RADII = (0.11, 0.16)
CHASM_CENTER = (0.07, 0.76)
CHASM_RADIUS = 0.10
HIGHWAY: tuple[Point, ...] = (
    (0.20, 0.50),
    (0.34, 0.50),
    (0.50, 0.50),
    (0.66, 0.50),
    (0.80, 0.56),
    (0.88, 0.46),
)


def _scale(point: Point) -> Point:
    return point[0] * GUIDE_SIZE[0], point[1] * GUIDE_SIZE[1]


def _wobble(points: tuple[Point, ...], rng: random.Random) -> list[Point]:
    scaled = [_scale(point) for point in points]
    result: list[Point] = []
    for start, end in itertools.pairwise(scaled):
        for step in range(EDGE_STEPS):
            ratio = step / EDGE_STEPS
            result.append(
                (
                    start[0]
                    + (end[0] - start[0]) * ratio
                    + rng.uniform(-EDGE_JITTER_PX, EDGE_JITTER_PX),
                    start[1] + (end[1] - start[1]) * ratio,
                )
            )
    result.append(scaled[-1])
    return result


def _fill_side(
    draw: ImageDraw.ImageDraw,
    edge: list[Point],
    outer_x: float,
    color: tuple[int, int, int],
) -> None:
    draw.polygon([*edge, (outer_x, GUIDE_SIZE[1]), (outer_x, 0)], fill=color)


def _draw_shallows(draw: ImageDraw.ImageDraw) -> None:
    center_x, center_y = _scale(SHALLOWS_CENTER)
    radius_x = SHALLOWS_RADII[0] * GUIDE_SIZE[0]
    radius_y = SHALLOWS_RADII[1] * GUIDE_SIZE[1]
    draw.ellipse(
        (
            center_x - radius_x,
            center_y - radius_y,
            center_x + radius_x,
            center_y + radius_y,
        ),
        fill=SHALLOWS,
    )


def _draw_tiers(draw: ImageDraw.ImageDraw) -> None:
    pairs = itertools.pairwise(TIER_BREAKS)
    for (top, bottom), color in zip(pairs, TIER_COLORS, strict=True):
        left_x, top_y = _scale((TERRACE_LEFT, top))
        _, bottom_y = _scale((TERRACE_LEFT, bottom))
        draw.rectangle((left_x, top_y, GUIDE_SIZE[0], bottom_y), fill=color)


def _draw_chasm(draw: ImageDraw.ImageDraw) -> None:
    center_x, center_y = _scale(CHASM_CENTER)
    radius = CHASM_RADIUS * GUIDE_SIZE[0]
    box = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    draw.ellipse(box, fill=CHASM)


def _draw_road(draw: ImageDraw.ImageDraw) -> None:
    line = [_scale(point) for point in HIGHWAY]
    draw.line(line, fill=ROAD, width=ROAD_HALF_WIDTH_PX * 2, joint="curve")


def build_guide_png() -> bytes:
    rng = random.Random(JITTER_SEED)
    image = Image.new("RGB", GUIDE_SIZE, PASS)
    draw = ImageDraw.Draw(image)
    _fill_side(draw, _wobble(CRAG_EDGE, rng), 0, CRAGS)
    _fill_side(draw, _wobble(VALLEY_EDGE, rng), GUIDE_SIZE[0], VALLEY)
    _draw_shallows(draw)
    _draw_tiers(draw)
    _draw_chasm(draw)
    _draw_road(draw)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
