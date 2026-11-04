"""The clock arithmetic and state schema every timed condition depends on."""

from scripts.night_desk import balance, schema, timeline


def test_the_night_is_twenty_one_turns() -> None:
    assert timeline.turns_to_dawn() == timeline.EXPECTED_TURN_COUNT == 21


def test_every_beat_lands_on_a_turn_boundary() -> None:
    assert all(minute % timeline.STEP == 0 for minute in timeline.BEATS.values())


def test_counts_close_each_act() -> None:
    assert timeline.COUNT_MINUTES == (120, 240, 360)
    assert timeline.ACT2_START == 120 + timeline.STEP
    assert timeline.ACT3_START == 240 + timeline.STEP


def test_drains_total_twelve() -> None:
    assert sum(drain.amount for drain in timeline.DRAINS) == 12


def test_every_drain_lands_on_a_turn_boundary() -> None:
    assert all(drain.start % timeline.STEP == 0 for drain in timeline.DRAINS)


def test_secrets_are_hidden() -> None:
    built = schema.build_state_schema()
    for root in (
        "seed",
        "cabin",
        "count",
        "check",
        "fragments",
        "visit",
        "flags",
        "events",
        "visited",
    ):
        assert built[root].get("hidden") is True
    for root in ("shift_minutes", "sanity", "tension_tier"):
        assert "hidden" not in built[root]


def test_schema_fields_the_data_doc_names() -> None:
    flat = schema.flatten_schema(schema.build_state_schema())
    assert flat["sanity"]["initial"] == 85
    assert flat["count.difference"]["initial"] == 1
    assert flat["visited.last"]["initial"] == "night_desk"
    assert flat["flags.hum"]["options"] == ["idle", "done"]
    assert flat["cabin.lamp"]["narrator_fact"] == "Cabin 14 lamp"
    assert flat["fragments.poster"]["options"] == ["locked", "shown"]
    assert flat["fragments.act2"]["initial"] == ""


def test_schema_exports() -> None:
    assert schema.RULE_IDS == ("r1", "r2", "r3", "r4", "r6", "r6_block", "r7", "r8")
    assert schema.INITIALLY_REVEALED == ("r1", "r2", "r3", "r4")
    assert schema.VISITOR_IDS == ("v1", "v2", "v3")
    assert schema.FRAGMENT_SLOTS == ("act1", "act2", "act3")


def test_v2_machinery_is_gone() -> None:
    flat = schema.flatten_schema(schema.build_state_schema())
    assert not any(path.startswith(("counters.", "regime.")) for path in flat)
    assert "fragments.cooldown" not in flat


def test_balance_amounts() -> None:
    assert (balance.SOFT_PENALTY, balance.CARDINAL_PENALTY) == (10, 15)
    assert balance.UNSAFE_ENTRY_PENALTY == 25
    assert (balance.HUM_GAIN, balance.HUM_LOSS) == (5, 25)
    assert balance.UNSIGNED_FOR_VISITOR_ENDING == 2
