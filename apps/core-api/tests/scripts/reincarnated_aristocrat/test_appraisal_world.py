from collections import Counter

from scripts.reincarnated_aristocrat import locations, maps
from scripts.seeding.types import MapSeed


def _all_maps() -> list[MapSeed]:
    return maps.map_seeds()


def test_there_are_28_locations_with_unique_slugs() -> None:
    assert len(locations.LOCATIONS) == 28
    assert len(set(locations.LOCATION_SLUGS)) == 28


def test_no_alias_is_shared_between_locations() -> None:
    names = [spec.name.lower() for spec in locations.LOCATIONS]
    aliases = [alias.lower() for spec in locations.LOCATIONS for alias in spec.aliases]
    duplicates = [key for key, count in Counter(names + aliases).items() if count > 1]
    assert duplicates == []


def test_every_location_has_exactly_one_pin() -> None:
    pinned = [pin.slug for seed in _all_maps() for pin in seed.pins]
    assert sorted(pinned) == sorted(locations.LOCATION_SLUGS)


def test_there_is_one_regional_map_and_seven_interiors() -> None:
    names = [seed.name for seed in _all_maps()]
    assert len(names) == 8
    assert len(set(names)) == 8
    assert names[0] == maps.REGIONAL_NAME


def test_exactly_one_start_pin_in_the_manor() -> None:
    starts = [seed for seed in _all_maps() if seed.start_slug]
    assert [seed.name for seed in starts] == ["Louvent Manor"]
    assert starts[0].start_slug in {pin.slug for pin in starts[0].pins}


def test_pin_positions_are_normalised() -> None:
    for seed in _all_maps():
        for pin in seed.pins:
            assert 0 < pin.x < 1
            assert 0 < pin.y < 1


def test_connections_join_known_locations_without_duplicates_or_loops() -> None:
    known = set(locations.LOCATION_SLUGS)
    seen: set[frozenset[str]] = set()
    for seed in _all_maps():
        for first, second in seed.connections:
            assert {first, second} <= known
            assert first != second
            pair = frozenset((first, second))
            assert pair not in seen, (first, second)
            seen.add(pair)


def test_every_interior_is_reachable_from_the_regional_map() -> None:
    interior_entrances = {second for _, second in maps.ENTRANCE_CONNECTIONS}
    interior_first_pins = {seed.pins[0].slug for seed in maps.interior_maps()}
    assert interior_first_pins <= interior_entrances | {"shadow_tavern"}


def test_no_two_pins_overlap_on_a_map() -> None:
    for seed in _all_maps():
        positions = [(pin.x, pin.y) for pin in seed.pins]
        assert len(set(positions)) == len(positions)
