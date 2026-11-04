from scripts.night_desk import prose


def test_rules_are_the_seven_v3_rules() -> None:
    assert list(prose.STANDING_INSTRUCTIONS) == [
        "r1",
        "r2",
        "r3",
        "r4",
        "r6",
        "r7",
        "r8",
    ]
    assert prose.STANDING_INSTRUCTIONS["r7"].endswith(
        "Do not read it. Leave it in the tray."
    )


def test_persona_carries_the_job_floor_plan_and_cast() -> None:
    for needle in (
        "three duties",
        "Floor 9",
        "Records room",
        "Margaret Hale",
        "Acknowledged.",
    ):
        assert needle in prose.PERSONA
    assert "Dungeon Master" not in prose.PERSONA


def test_opening_states_three_jobs_and_the_plate() -> None:
    assert "You have three jobs tonight" in prose.OPENING_SCENE
    assert "Mr. Orr is in." in prose.OPENING_SCENE
    assert "{player_name}" in prose.OPENING_SCENE


def test_opening_has_the_music_that_will_not_stop() -> None:
    assert "It won't stop." in prose.OPENING_SCENE


def test_no_canon_leaks_into_any_text() -> None:
    texts = [
        prose.PERSONA,
        prose.OPENING_SCENE,
        *prose.FRAGMENT_EVIDENCE.values(),
        *prose.BEATS.values(),
    ]
    for forbidden in (
        "Tallis is",
        "absorbed",
        "soul",
        "humanity",
        "taken into TrueFeel",
    ):
        assert not any(forbidden in text for text in texts)


def test_four_endings() -> None:
    assert [ending.title for ending in prose.ENDINGS.values()] == [
        "Counted",
        "Mr. Orr Is In",
        "Visitor",
        "Don't Be Late",
    ]


def test_three_visitors_with_their_told_times() -> None:
    told = {key: v.told_minute_of_day for key, v in prose.VISITORS.items()}
    assert told == {"v1": 1411, "v2": 82, "v3": 232}
    assert all(v.stays_for_turns == 3 for v in prose.VISITORS.values())


def test_three_duties_and_the_hum_texts() -> None:
    assert len(prose.DUTIES) == 3
    assert prose.HUM_WIN_TEXT == "You hum until the chime."
    assert prose.HUM_LOSE_TEXT == "You answer the voice."


def test_takeover_lines_and_fragments() -> None:
    assert prose.TAKEOVER_LINES == ("Get me out of here, Orr", "I feel too much")
    assert list(prose.FRAGMENT_EVIDENCE) == [
        "poster",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
    ]


def test_persona_has_concrete_variety_and_accuracy_rules() -> None:
    for needle in (
        "End on the new detail, or on something someone says or does.",
        "Do not end a turn by listing what the player can do.",
        "Never end a turn by describing the room.",
        "Do not end two turns in a row with the same kind of sentence.",
        "at most once every three turns",
        'Do not start two turns in a row with "You".',
        "Never write a clock time yourself",
        "Do not use asterisks",
        "Never say the lamp goes dark",
    ):
        assert needle in prose.PERSONA, needle


def test_ambient_deck_has_one_plain_line_per_turn() -> None:
    import re

    assert len(prose.AMBIENT_DECK) == 21
    assert len(set(prose.AMBIENT_DECK)) == 21
    for line in prose.AMBIENT_DECK:
        assert len(line) <= 90, line
        assert "*" not in line
        assert not re.search(r"\d", line), "no numbers or clock times in the deck"
    assert "{line}" in prose.AMBIENT_TEMPLATE


def test_persona_no_longer_asks_for_the_next_action_to_be_spelled_out() -> None:
    assert "always know what they could do next" not in prose.PERSONA
    assert "always know what job is waiting" in prose.PERSONA
    assert "End with the next thing the player can do" not in prose.PERSONA
