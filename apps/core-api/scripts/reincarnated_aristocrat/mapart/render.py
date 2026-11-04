from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageDraw
from scripts.reincarnated_aristocrat.mapart.constants import (
    BORDER_INSET_PX,
    CANVAS_SIZE,
    GLYPH_LIFT_PX,
    PIN_GLYPH_SIZE,
)
from scripts.reincarnated_aristocrat.mapart.decor import DECOR, PIN_GLYPHS
from scripts.reincarnated_aristocrat.mapart.glyphs import draw_glyph
from scripts.reincarnated_aristocrat.mapart.ground import draw_ground
from scripts.reincarnated_aristocrat.mapart.naming import map_file_name
from scripts.reincarnated_aristocrat.mapart.parchment import (
    draw_border,
    make_paper,
)
from scripts.seeding.types import MapSeed


def _to_pixels(x: float, y: float) -> tuple[int, int]:
    return int(x * CANVAS_SIZE[0]), int(y * CANVAS_SIZE[1])


def _draw_decor(draw: ImageDraw.ImageDraw, seed: MapSeed) -> None:
    for item in sorted(DECOR[seed.name], key=lambda entry: entry.y):
        draw_glyph(draw, item.kind, _to_pixels(item.x, item.y), item.size)


def _draw_pin_glyphs(draw: ImageDraw.ImageDraw, seed: MapSeed) -> None:
    for pin in sorted(seed.pins, key=lambda entry: entry.y):
        pin_x, pin_y = _to_pixels(pin.x, pin.y)
        center = (pin_x, pin_y - GLYPH_LIFT_PX)
        draw_glyph(draw, PIN_GLYPHS[pin.slug], center, PIN_GLYPH_SIZE)


def _inner_frame_mask() -> Image.Image:
    mask = Image.new("L", CANVAS_SIZE, 0)
    width, height = CANVAS_SIZE
    inset = BORDER_INSET_PX
    ImageDraw.Draw(mask).rectangle(
        (inset, inset, width - inset, height - inset), fill=255
    )
    return mask


def render_map(seed: MapSeed) -> Image.Image:
    paper = make_paper(seed.name)
    canvas = paper.copy()
    draw = ImageDraw.Draw(canvas)
    draw_ground(draw, seed)
    _draw_decor(draw, seed)
    _draw_pin_glyphs(draw, seed)
    image = Image.composite(canvas, paper, _inner_frame_mask())
    draw_border(image)
    return image


def render_all(seeds: Sequence[MapSeed], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seed in seeds:
        path = output_dir / map_file_name(seed)
        render_map(seed).save(path, format="PNG", optimize=True)
        written.append(path)
    return written
