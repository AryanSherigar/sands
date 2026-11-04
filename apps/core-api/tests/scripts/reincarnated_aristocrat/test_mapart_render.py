from pathlib import Path

from PIL import Image, ImageChops, ImageDraw
from scripts.reincarnated_aristocrat import maps
from scripts.reincarnated_aristocrat.mapart.constants import CANVAS_SIZE
from scripts.reincarnated_aristocrat.mapart.glyphs import GlyphKind, draw_glyph
from scripts.reincarnated_aristocrat.mapart.parchment import make_parchment
from scripts.reincarnated_aristocrat.mapart.render import render_all


def test_parchment_has_canvas_size_and_is_deterministic() -> None:
    first = make_parchment("Louvent Manor")
    second = make_parchment("Louvent Manor")
    assert first.size == CANVAS_SIZE
    assert first.tobytes() == second.tobytes()


def test_parchment_differs_between_maps() -> None:
    assert make_parchment("a").tobytes() != make_parchment("b").tobytes()


def test_every_glyph_draws_ink_inside_its_reported_box() -> None:
    size = 60
    for kind in GlyphKind:
        image = Image.new("RGB", (400, 400), "white")
        box = draw_glyph(ImageDraw.Draw(image), kind, (200, 200), size)
        left, top, right, bottom = box
        assert 0 <= left < right <= 400, kind
        assert 0 <= top < bottom <= 400, kind
        assert right - left <= size * 4, kind
        assert ImageChops.invert(image).getbbox() is not None, kind


def test_render_all_writes_one_png_per_map(tmp_path: Path) -> None:
    seeds = maps.map_seeds(with_images=False)
    written = render_all(seeds, tmp_path)
    assert len(written) == len(seeds) == 8
    assert all(path.is_file() and path.stat().st_size > 10_000 for path in written)
