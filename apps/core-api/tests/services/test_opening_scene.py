from app.services.opening_scene import render_opening_scene


def test_player_name_token_is_replaced():
    assert (
        render_opening_scene("Welcome, {player_name}. The desk is yours.", "Mara")
        == "Welcome, Mara. The desk is yours."
    )


def test_every_occurrence_is_replaced():
    assert render_opening_scene("{player_name} and {player_name}", "Ik") == "Ik and Ik"


def test_unknown_braces_are_left_untouched():
    text = "Rule {rule_id} says {player_name}: {0} {{x}}"

    assert render_opening_scene(text, "Mara") == "Rule {rule_id} says Mara: {0} {{x}}"


def test_missing_or_blank_scene_yields_none():
    assert render_opening_scene(None, "Mara") is None
    assert render_opening_scene("   ", "Mara") is None


def test_blank_name_falls_back_to_adventurer():
    assert render_opening_scene("Hi {player_name}", "  ") == "Hi Adventurer"


def test_name_containing_braces_is_inserted_literally():
    assert render_opening_scene("Hi {player_name}", "{x}") == "Hi {x}"


def test_long_text_is_preserved():
    body = "word " * 5000

    assert render_opening_scene(body + "{player_name}", "Mara") == body + "Mara"
