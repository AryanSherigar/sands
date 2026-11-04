from scripts.reincarnated_aristocrat import maps
from scripts.reincarnated_aristocrat.mapart import decor
from scripts.reincarnated_aristocrat.mapart.constants import CANVAS_SIZE, LABEL_BOX
from scripts.reincarnated_aristocrat.mapart.naming import map_file_name
from scripts.reincarnated_aristocrat.mapart.render import render_map

HALF_LABEL_WIDTH = LABEL_BOX[0] // 2
HALF_LABEL_HEIGHT = LABEL_BOX[1] // 2


def to_pixels(x: float, y: float) -> tuple[int, int]:
    return int(x * CANVAS_SIZE[0]), int(y * CANVAS_SIZE[1])


def test_every_map_has_decor_and_every_pin_has_a_glyph() -> None:
    for seed in maps.map_seeds():
        assert seed.name in decor.DECOR
        for pin in seed.pins:
            assert pin.slug in decor.PIN_GLYPHS


def test_decor_never_covers_a_pin_label_box() -> None:
    for seed in maps.map_seeds():
        for item in decor.DECOR[seed.name]:
            item_x, item_y = to_pixels(item.x, item.y)
            for pin in seed.pins:
                pin_x, pin_y = to_pixels(pin.x, pin.y)
                is_overlapping_x = abs(item_x - pin_x) < HALF_LABEL_WIDTH + item.size
                is_overlapping_y = abs(item_y - pin_y) < HALF_LABEL_HEIGHT + item.size
                assert not (is_overlapping_x and is_overlapping_y), (
                    seed.name,
                    pin.slug,
                )


def test_label_boxes_stay_inside_the_canvas() -> None:
    for seed in maps.map_seeds():
        for pin in seed.pins:
            pin_x, pin_y = to_pixels(pin.x, pin.y)
            assert HALF_LABEL_WIDTH <= pin_x <= CANVAS_SIZE[0] - HALF_LABEL_WIDTH
            assert HALF_LABEL_HEIGHT <= pin_y <= CANVAS_SIZE[1] - HALF_LABEL_HEIGHT


def test_decor_stays_inside_the_canvas() -> None:
    for name, items in decor.DECOR.items():
        for item in items:
            assert 0.0 < item.x < 1.0 and 0.0 < item.y < 1.0, name


def test_render_is_deterministic_and_correct_size() -> None:
    seed = maps.regional_map()
    first, second = render_map(seed), render_map(seed)
    assert first.size == CANVAS_SIZE
    assert first.tobytes() == second.tobytes()


def test_file_names_are_unique_lowercase_slugs() -> None:
    names = [map_file_name(seed) for seed in maps.map_seeds()]
    assert len(set(names)) == len(names)
    assert all(name.endswith(".png") and name == name.lower() for name in names)
    assert "the-shadows-haunt.png" in names
