import random

from PIL import Image, ImageDraw
from scripts.reincarnated_aristocrat.mapart.constants import (
    BORDER_INSET_PX,
    BORDER_WIDTH_PX,
    CANVAS_SIZE,
    PALETTE,
    TONE_ALPHA,
    TONE_GRID,
    VIGNETTE_ALPHA,
)

TONE_MIN = 90
TONE_MAX = 200


def _tone_layer(rng: random.Random) -> Image.Image:
    width, height = TONE_GRID
    grid = Image.new("L", TONE_GRID)
    grid.putdata([rng.randint(TONE_MIN, TONE_MAX) for _ in range(width * height)])
    return grid.resize(CANVAS_SIZE, Image.Resampling.BICUBIC).convert("RGB")


def _vignette(base: Image.Image) -> Image.Image:
    mask = Image.radial_gradient("L").resize(CANVAS_SIZE)
    mask = mask.point(lambda value: int(value * VIGNETTE_ALPHA))
    edge = Image.new("RGB", CANVAS_SIZE, PALETTE["paper_edge"])
    return Image.composite(edge, base, mask)


def draw_border(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    width, height = CANVAS_SIZE
    for inset in (BORDER_INSET_PX, BORDER_INSET_PX + 2 * BORDER_WIDTH_PX):
        draw.rectangle(
            (inset, inset, width - inset, height - inset),
            outline=PALETTE["ink_faint"],
            width=BORDER_WIDTH_PX // 2,
        )


def make_paper(seed_text: str) -> Image.Image:
    rng = random.Random(seed_text)
    paper = Image.new("RGB", CANVAS_SIZE, PALETTE["paper"])
    toned = Image.blend(paper, _tone_layer(rng), TONE_ALPHA)
    return _vignette(toned)


def make_parchment(seed_text: str) -> Image.Image:
    image = make_paper(seed_text)
    draw_border(image)
    return image
