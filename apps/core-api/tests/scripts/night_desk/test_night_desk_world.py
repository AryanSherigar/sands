from scripts.night_desk import entities, map_data

LOCATION_SLUGS = {
    "elevator_lobby",
    "night_desk",
    "east_corridor",
    "east_alcove",
    "records_room",
    "cabin_approach",
    "cabin_14",
    "print_room",
    "stairwell_door",
}


def test_records_room_is_off_the_corridor_and_the_cage_is_gone() -> None:
    assert ("east_corridor", "records_room") in map_data.CONNECTIONS
    assert all(
        "records_cage" not in pair and "bullpen" not in pair
        for pair in map_data.CONNECTIONS
    )


def test_corridor_hangs_off_the_night_desk() -> None:
    assert ("night_desk", "east_corridor") in map_data.CONNECTIONS
    assert len(map_data.CONNECTIONS) == 8


def test_nine_pins_at_the_data_doc_positions() -> None:
    pins = {pin.slug: (pin.x, pin.y) for pin in map_data.PINS}
    assert set(pins) == LOCATION_SLUGS
    assert pins["records_room"] == (0.62, 0.52)
    assert pins["cabin_14"] == (0.95, 0.30)


def test_cast_has_three_named_visitors_and_no_occupant() -> None:
    slugs = {seed.slug for seed in entities.entity_seeds()}
    assert {"visitor_margaret", "visitor_daniel", "visitor_ruth", "mr_orr"} <= slugs
    assert "cabin_occupant" not in slugs
    assert slugs >= LOCATION_SLUGS


def test_canonical_location_names_are_what_the_night_driver_moves_by() -> None:
    names = {seed.slug: seed.payload.canonical_name for seed in entities.entity_seeds()}
    assert names["night_desk"] == "The night desk"
    assert names["cabin_approach"] == "Outside Cabin 14"
    assert names["records_room"] == "Records room"


def test_records_and_print_room_aliases() -> None:
    aliases = {seed.slug: seed.payload.aliases for seed in entities.entity_seeds()}
    assert "the filing room" in aliases["records_room"]
    assert "the printer" in aliases["print_room"]
    assert "the poster" in aliases["elevator_lobby"]


def test_facts_name_eva_the_door_and_the_cabin() -> None:
    predicates = {fact.predicate for fact in entities.fact_seeds()}
    assert predicates == {"works_at", "locked_until", "part_of"}
